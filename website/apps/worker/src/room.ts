// GameRoom Durable Object：每个房号一个实例，持有权威游戏状态。
// - 谜底只存在这里，下发给客户端的 RoomView 在 reveal/finished 之前不含答案
// - 计时全部由 DO alarm 驱动（回合超时、揭晓后进入下一轮、匹配房开局）
// - 使用 WebSocket Hibernation，空闲房间不常驻内存；状态持久化在 ctx.storage

import { DurableObject } from 'cloudflare:workers'
import {
  GUESS_COOLDOWN_MS,
  MAX_PLAYERS,
  REVEAL_SECONDS,
  ROUND_SECONDS,
  ROUNDS_PER_GAME,
  SOLVE_POINTS,
  cleanGuess,
  type ClientMessage,
  type GuessView,
  type Phase,
  type RoomMode,
  type RoomView,
  type ServerMessage,
} from '@wtf/shared'
import type { Env } from './env'
import { judge } from './judge'
import { randomPuzzle, type Puzzle } from './puzzles'

/** 匹配房：等人到齐的最长时间 */
const MATCH_JOIN_GRACE_MS = 15_000
const MAX_GUESSES_KEPT = 60

type AlarmAction = 'roundTimeout' | 'nextRound' | 'matchStart'

interface PlayerData {
  uid: string
  name: string
  score: number
  roundBest: number
}

interface RoomData {
  code: string
  mode: RoomMode
  phase: Phase
  hostUid: string | null
  expectedPlayers: number
  round: number
  puzzle: Puzzle | null
  usedIds: string[]
  revealed: (string | null)[]
  guesses: GuessView[]
  players: PlayerData[]
  deadline: number | null
  solvedBy: string | null
  previousAnswer: string | null
  alarmAction: AlarmAction | null
}

interface Attachment {
  uid: string
  name: string
}

export class GameRoom extends DurableObject<Env> {
  private data: RoomData | null = null
  private lastGuessAt = new Map<string, number>()

  private async load(): Promise<RoomData | null> {
    if (!this.data) this.data = (await this.ctx.storage.get<RoomData>('room')) ?? null
    return this.data
  }

  private async save() {
    if (this.data) await this.ctx.storage.put('room', this.data)
  }

  private async schedule(action: AlarmAction | null, at?: number) {
    const d = this.data!
    d.alarmAction = action
    if (action && at) await this.ctx.storage.setAlarm(at)
    else await this.ctx.storage.deleteAlarm()
  }

  // ---------------- HTTP 入口（由 Worker 路由转发） ----------------

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url)

    if (url.pathname === '/init') {
      if (await this.load()) return new Response('exists', { status: 409 })
      const { code, mode, expectedPlayers } = (await request.json()) as {
        code: string
        mode: RoomMode
        expectedPlayers?: number
      }
      this.data = {
        code,
        mode,
        phase: 'lobby',
        hostUid: null,
        expectedPlayers: expectedPlayers ?? 0,
        round: 0,
        puzzle: null,
        usedIds: [],
        revealed: [],
        guesses: [],
        players: [],
        deadline: null,
        solvedBy: null,
        previousAnswer: null,
        alarmAction: null,
      }
      if (mode === 'match') await this.schedule('matchStart', Date.now() + MATCH_JOIN_GRACE_MS)
      await this.save()
      return new Response('ok')
    }

    if (url.pathname === '/info') {
      const d = await this.load()
      if (!d) return new Response('not found', { status: 404 })
      return Response.json({ code: d.code, mode: d.mode, phase: d.phase, players: d.players.length })
    }

    if (url.pathname === '/connect') {
      if (request.headers.get('Upgrade') !== 'websocket') {
        return new Response('expected websocket', { status: 426 })
      }
      const d = await this.load()
      if (!d) return new Response('room not found', { status: 404 })

      const uid = url.searchParams.get('uid') ?? ''
      const name = url.searchParams.get('name') ?? ''
      const known = d.players.some((p) => p.uid === uid)
      const limit = d.mode === 'solo' ? 1 : MAX_PLAYERS
      if (!known && d.players.length >= limit) return new Response('room full', { status: 403 })
      if (!known && d.mode === 'match' && d.phase !== 'lobby') {
        return new Response('game already started', { status: 403 })
      }

      const pair = new WebSocketPair()
      const [client, server] = [pair[0], pair[1]]
      // 同一 uid 重连时踢掉旧连接
      for (const ws of this.ctx.getWebSockets(uid)) ws.close(4000, 'replaced')
      this.ctx.acceptWebSocket(server, [uid])
      server.serializeAttachment({ uid, name } satisfies Attachment)

      await this.onJoin(uid, name)
      return new Response(null, { status: 101, webSocket: client })
    }

    return new Response('not found', { status: 404 })
  }

  // ---------------- WebSocket 事件 ----------------

  async webSocketMessage(ws: WebSocket, raw: string | ArrayBuffer) {
    const d = await this.load()
    if (!d || typeof raw !== 'string') return
    const { uid } = ws.deserializeAttachment() as Attachment

    let msg: ClientMessage
    try {
      msg = JSON.parse(raw)
    } catch {
      return
    }

    switch (msg.event) {
      case 'ping':
        return this.send(ws, { event: 'pong' })
      case 'game:start':
        if (d.phase !== 'lobby' || !this.canControl(uid)) return
        await this.startGame()
        return
      case 'game:restart':
        if (d.phase !== 'finished' || !this.canControl(uid)) return
        await this.startGame()
        return
      case 'game:skip':
        if (d.phase !== 'playing' || !this.canControl(uid)) return
        await this.endRound(null)
        return
      case 'game:guess':
        await this.onGuess(ws, uid, String(msg.data?.guess ?? ''))
        return
    }
  }

  async webSocketClose(ws: WebSocket) {
    await this.load()
    ws.close()
    this.broadcastState()
  }

  async webSocketError(ws: WebSocket) {
    await this.webSocketClose(ws)
  }

  async alarm() {
    const d = await this.load()
    if (!d) return

    if (this.openSockets().length === 0) {
      // 无人在线：直接清空房间，避免空跑计费
      await this.ctx.storage.deleteAll()
      this.data = null
      return
    }

    const action = d.alarmAction
    d.alarmAction = null
    if (action === 'matchStart' && d.phase === 'lobby') await this.startGame()
    else if (action === 'roundTimeout' && d.phase === 'playing') await this.endRound(null)
    else if (action === 'nextRound' && d.phase === 'reveal') await this.nextRound()
    else await this.save()
  }

  // ---------------- 游戏流程 ----------------

  private canControl(uid: string) {
    const d = this.data!
    return d.mode === 'solo' || d.hostUid === uid
  }

  private async onJoin(uid: string, name: string) {
    const d = this.data!
    const existing = d.players.find((p) => p.uid === uid)
    if (existing) existing.name = name
    else d.players.push({ uid, name, score: 0, roundBest: 0 })
    if (!d.hostUid) d.hostUid = uid

    const matchReady = d.mode === 'match' && d.players.length >= d.expectedPlayers
    if (d.phase === 'lobby' && (d.mode === 'solo' || matchReady)) {
      await this.startGame()
    } else {
      await this.save()
      this.broadcastState()
    }
  }

  private async startGame() {
    const d = this.data!
    d.round = 0
    d.usedIds = []
    d.previousAnswer = null
    for (const p of d.players) p.score = 0
    await this.nextRound()
  }

  private async nextRound() {
    const d = this.data!
    if (d.round >= ROUNDS_PER_GAME) {
      d.phase = 'finished'
      d.deadline = null
      await this.schedule(null)
      await this.save()
      this.broadcastState()
      return
    }

    const puzzle = randomPuzzle({ category: d.puzzle?.category, ids: d.usedIds })
    d.round += 1
    d.puzzle = puzzle
    d.usedIds.push(puzzle.id)
    d.phase = 'playing'
    d.revealed = Array(puzzle.word.length).fill(null)
    d.guesses = []
    d.solvedBy = null
    d.deadline = Date.now() + ROUND_SECONDS * 1000
    for (const p of d.players) p.roundBest = 0

    await this.schedule('roundTimeout', d.deadline)
    await this.save()
    this.broadcastState()
  }

  /** solver 为 null 表示超时或跳过 */
  private async endRound(solver: PlayerData | null) {
    const d = this.data!
    d.phase = 'reveal'
    d.deadline = null
    d.solvedBy = solver?.name ?? null
    for (const p of d.players) {
      p.score += p === solver ? SOLVE_POINTS : Math.floor((p.roundBest * 100) / 10)
    }
    d.previousAnswer = d.puzzle?.word ?? null

    await this.schedule('nextRound', Date.now() + REVEAL_SECONDS * 1000)
    await this.save()
    this.broadcastState()
  }

  private async onGuess(ws: WebSocket, uid: string, raw: string) {
    const d = this.data!
    if (d.phase !== 'playing' || !d.puzzle) return

    const cleaned = cleanGuess(raw, d.puzzle.word.length)
    if (!cleaned.ok) return this.send(ws, { event: 'error', data: { message: cleaned.reason } })
    const guess = cleaned.word

    const now = Date.now()
    if (now - (this.lastGuessAt.get(uid) ?? 0) < GUESS_COOLDOWN_MS) {
      return this.send(ws, { event: 'error', data: { message: '猜得太快了，稍等一下' } })
    }
    if (d.guesses.some((g) => g.uid === uid && g.guess === guess)) {
      return this.send(ws, { event: 'error', data: { message: '你已经猜过这个词了' } })
    }
    this.lastGuessAt.set(uid, now)

    const puzzle = d.puzzle
    let verdict
    try {
      verdict = await judge(this.env, puzzle, guess)
    } catch (err) {
      console.error('judge failed', err)
      this.lastGuessAt.delete(uid)
      return this.send(ws, { event: 'error', data: { message: '判定服务繁忙，请重试（不计次数）' } })
    }

    // await 期间可能已换题或已有人猜中
    if (d.phase !== 'playing' || d.puzzle?.id !== puzzle.id) return

    const player = d.players.find((p) => p.uid === uid)
    if (!player) return
    player.roundBest = Math.max(player.roundBest, verdict.affinity)

    ;[...guess].forEach((ch, i) => {
      if (ch === puzzle.word[i]) d.revealed[i] = ch
    })

    const record: GuessView = { uid, name: player.name, guess, affinity: verdict.affinity, ts: now }
    d.guesses.unshift(record)
    d.guesses.length = Math.min(d.guesses.length, MAX_GUESSES_KEPT)
    this.broadcast({ event: 'game:guessResult', data: record })

    if (verdict.solved) await this.endRound(player)
    else {
      await this.save()
      this.broadcastState()
    }
  }

  // ---------------- 下发 ----------------

  private view(): RoomView {
    const d = this.data!
    const online = new Set(
      this.openSockets().map((ws) => (ws.deserializeAttachment() as Attachment).uid),
    )
    const showAnswer = d.phase === 'reveal' || d.phase === 'finished'
    return {
      code: d.code,
      mode: d.mode,
      phase: d.phase,
      hostUid: d.hostUid,
      round: d.round,
      roundsTotal: ROUNDS_PER_GAME,
      puzzle: d.puzzle
        ? { id: d.puzzle.id, wordLength: d.puzzle.wordLength, category: d.puzzle.category }
        : null,
      revealed: d.revealed,
      guesses: d.guesses,
      players: d.players
        .map((p) => ({ ...p, online: online.has(p.uid) }))
        .sort((a, b) => b.score - a.score),
      deadline: d.deadline,
      now: Date.now(),
      answer: showAnswer ? (d.puzzle?.word ?? null) : null,
      solvedBy: d.solvedBy,
      previousAnswer: d.phase === 'playing' ? d.previousAnswer : null,
    }
  }

  /** close 回调期间旧连接仍在 getWebSockets() 中，需按 readyState 过滤 */
  private openSockets() {
    return this.ctx.getWebSockets().filter((ws) => ws.readyState === WebSocket.OPEN)
  }

  private send(ws: WebSocket, msg: ServerMessage) {
    try {
      ws.send(JSON.stringify(msg))
    } catch {
      /* 连接已断开 */
    }
  }

  private broadcast(msg: ServerMessage) {
    const text = JSON.stringify(msg)
    for (const ws of this.openSockets()) {
      try {
        ws.send(text)
      } catch {
        /* ignore */
      }
    }
  }

  private broadcastState() {
    if (this.data) this.broadcast({ event: 'room:state', data: this.view() })
  }
}
