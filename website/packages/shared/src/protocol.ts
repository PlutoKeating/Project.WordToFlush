// 前端 <-> Worker 通信协议。WebSocket 消息统一为 { event, data }。
// 谜底原文只在 phase === 'reveal' / 'finished' 时通过 answer 字段下发。

export type RoomMode = 'solo' | 'private' | 'match'
export type Phase = 'lobby' | 'playing' | 'reveal' | 'finished'

export interface PublicPuzzle {
  id: string
  wordLength: number
  category: string
}

export interface PlayerView {
  uid: string
  name: string
  score: number
  /** 本轮最高关联度 0..1 */
  roundBest: number
  online: boolean
}

export interface GuessView {
  uid: string
  name: string
  guess: string
  /** 0..1 */
  affinity: number
  ts: number
}

export interface RoomView {
  code: string
  mode: RoomMode
  phase: Phase
  hostUid: string | null
  round: number
  roundsTotal: number
  puzzle: PublicPuzzle | null
  /** 每个字位：已揭示的汉字或 null */
  revealed: (string | null)[]
  /** 本轮所有猜测，按时间倒序 */
  guesses: GuessView[]
  players: PlayerView[]
  /** 本轮截止时间（epoch ms），非 playing 时为 null */
  deadline: number | null
  /** 当前服务器时间，供前端校正时钟偏差 */
  now: number
  /** 仅 reveal / finished 阶段有值 */
  answer: string | null
  solvedBy: string | null
  previousAnswer: string | null
}

// ---------- 客户端 -> 服务端 ----------
export type ClientMessage =
  | { event: 'game:start' }
  | { event: 'game:guess'; data: { guess: string } }
  | { event: 'game:skip' }
  | { event: 'game:restart' }
  | { event: 'ping' }

// ---------- 服务端 -> 客户端 ----------
export type ServerMessage =
  | { event: 'room:state'; data: RoomView }
  | { event: 'game:guessResult'; data: GuessView }
  | { event: 'error'; data: { message: string } }
  | { event: 'pong' }

// ---------- 随机匹配 WebSocket ----------
export type MatchServerMessage =
  | { event: 'match:waiting'; data: { count: number; startsAt: number | null } }
  | { event: 'match:found'; data: { code: string } }

// ---------- REST ----------
export interface CreateRoomRequest {
  mode: 'solo' | 'private'
}
export interface CreateRoomResponse {
  code: string
}
