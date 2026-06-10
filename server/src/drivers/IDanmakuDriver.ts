import type { Platform } from '@shared/types/game'

export interface DanmakuMessage {
  userId: string
  userName: string
  content: string
  timestamp: number
}

export interface IDanmakuDriver {
  readonly platform: Platform

  connect(roomId: string): Promise<void>
  disconnect(): void
  onDanmaku(callback: (msg: DanmakuMessage) => void): void
}
