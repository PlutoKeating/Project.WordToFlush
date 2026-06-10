import type { Platform } from '@shared/types/game'
import { IDanmakuDriver, DanmakuMessage } from './IDanmakuDriver'

export class KuaishouDriver implements IDanmakuDriver {
  readonly platform: Platform = 'kuaishou'
  private roomId: string = ''
  private callbacks: ((msg: DanmakuMessage) => void)[] = []

  async connect(roomId: string): Promise<void> {
    this.roomId = roomId
    console.log(`[KuaishouDriver] Connected to room ${roomId}`)
  }

  disconnect(): void {
    this.callbacks = []
    console.log(`[KuaishouDriver] Disconnected from room ${this.roomId}`)
  }

  onDanmaku(callback: (msg: DanmakuMessage) => void): void {
    this.callbacks.push(callback)
  }
}
