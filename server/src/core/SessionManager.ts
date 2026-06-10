import type { Platform, RoomState } from '@shared/types/game'
import { GameMaster } from './GameMaster'

export class SessionManager {
  private rooms: Map<string, RoomState> = new Map()
  private gameMaster: GameMaster

  constructor(gameMaster: GameMaster) {
    this.gameMaster = gameMaster
  }

  async createRoom(roomId: string, platform: Platform): Promise<RoomState> {
    if (this.rooms.has(roomId)) {
      return this.rooms.get(roomId)!
    }

    const roomState = await this.gameMaster.createRoom(roomId, platform)
    this.rooms.set(roomId, roomState)
    return roomState
  }

  getRoom(roomId: string): RoomState | undefined {
    return this.rooms.get(roomId)
  }

  async nextPuzzle(roomId: string): Promise<RoomState | null> {
    const room = this.rooms.get(roomId)
    if (!room) return null

    const puzzle = await this.gameMaster.nextPuzzle(roomId, room)
    this.rooms.set(roomId, room)
    return room
  }

  removeRoom(roomId: string): void {
    this.rooms.delete(roomId)
  }

  getActiveRooms(): string[] {
    return Array.from(this.rooms.keys())
  }
}
