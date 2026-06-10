import { Server, Socket } from 'socket.io'
import { SessionManager } from '../core/SessionManager'
import type { Platform } from '@shared/types/game'

export class SocketHandler {
  private io: Server
  private sessionManager: SessionManager

  constructor(io: Server, sessionManager: SessionManager) {
    this.io = io
    this.sessionManager = sessionManager
  }

  register(): void {
    this.io.on('connection', (socket: Socket) => {
      console.log(`[Socket] Client connected: ${socket.id}`)

      socket.on('room:join', async (data: { roomId: string; platform: Platform }) => {
        socket.join(data.roomId)
        const roomState = await this.sessionManager.createRoom(data.roomId, data.platform)
        this.io.to(data.roomId).emit('game:state', roomState)
      })

      socket.on('room:leave', (data: { roomId: string }) => {
        socket.leave(data.roomId)
      })

      socket.on('game:nextPuzzle', async (data: { roomId: string }) => {
        const roomState = await this.sessionManager.nextPuzzle(data.roomId)
        if (roomState?.currentPuzzle) {
          this.io.to(data.roomId).emit('game:newPuzzle', roomState.currentPuzzle)
          this.io.to(data.roomId).emit('game:state', roomState)
        }
      })

      socket.on('disconnect', () => {
        console.log(`[Socket] Client disconnected: ${socket.id}`)
      })
    })
  }
}
