// Matchmaker Durable Object（全局单例 "global"）：维护随机匹配等待队列。
// 满 MATCH_FULL_PLAYERS 人立即成局；否则首个玩家等待 MATCH_WAIT_SECONDS 后，
// 只要人数 >= MATCH_MIN_PLAYERS 就成局。成局后下发房号并关闭排队连接。

import { DurableObject } from 'cloudflare:workers'
import {
  MATCH_FULL_PLAYERS,
  MATCH_MIN_PLAYERS,
  MATCH_WAIT_SECONDS,
  type MatchServerMessage,
} from '@wtf/shared'
import type { Env } from './env'
import { createRoom } from './rooms'

interface Ticket {
  uid: string
  joinedAt: number
}

export class Matchmaker extends DurableObject<Env> {
  private queue(): WebSocket[] {
    return this.ctx
      .getWebSockets()
      .filter((ws) => ws.readyState === WebSocket.OPEN)
      .sort(
        (a, b) =>
          (a.deserializeAttachment() as Ticket).joinedAt - (b.deserializeAttachment() as Ticket).joinedAt,
      )
  }

  async fetch(request: Request): Promise<Response> {
    if (request.headers.get('Upgrade') !== 'websocket') {
      return new Response('expected websocket', { status: 426 })
    }
    const uid = new URL(request.url).searchParams.get('uid') ?? ''
    for (const ws of this.ctx.getWebSockets(uid)) ws.close(4000, 'replaced')

    const pair = new WebSocketPair()
    this.ctx.acceptWebSocket(pair[1], [uid])
    pair[1].serializeAttachment({ uid, joinedAt: Date.now() } satisfies Ticket)

    await this.tryMatch()
    return new Response(null, { status: 101, webSocket: pair[0] })
  }

  async webSocketMessage() {
    /* 排队期间客户端无需发送消息 */
  }

  async webSocketClose(ws: WebSocket) {
    ws.close()
    await this.tryMatch()
  }

  async alarm() {
    await this.tryMatch()
  }

  private async tryMatch() {
    let queue = this.queue()

    while (queue.length >= MATCH_FULL_PLAYERS) {
      await this.formRoom(queue.slice(0, MATCH_FULL_PLAYERS))
      queue = this.queue()
    }

    const startsAt = queue.length
      ? (queue[0].deserializeAttachment() as Ticket).joinedAt + MATCH_WAIT_SECONDS * 1000
      : null

    if (startsAt && queue.length >= MATCH_MIN_PLAYERS && Date.now() >= startsAt) {
      await this.formRoom(queue)
      queue = this.queue()
    }

    if (queue.length) {
      const firstAt = (queue[0].deserializeAttachment() as Ticket).joinedAt + MATCH_WAIT_SECONDS * 1000
      // 人数不足时到点后也要再检查一次，届时若仍不足则顺延
      await this.ctx.storage.setAlarm(Math.max(firstAt, Date.now() + 5000))
      const msg: MatchServerMessage = {
        event: 'match:waiting',
        data: { count: queue.length, startsAt: queue.length >= MATCH_MIN_PLAYERS ? firstAt : null },
      }
      for (const ws of queue) ws.send(JSON.stringify(msg))
    } else {
      await this.ctx.storage.deleteAlarm()
    }
  }

  private async formRoom(members: WebSocket[]) {
    const code = await createRoom(this.env, 'match', members.length)
    const msg = JSON.stringify({ event: 'match:found', data: { code } } satisfies MatchServerMessage)
    for (const ws of members) {
      ws.send(msg)
      ws.close(1000, 'matched')
    }
  }
}
