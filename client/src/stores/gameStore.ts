import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { io, Socket } from 'socket.io-client'
import type { RoomState, WordPuzzle, GuessRecord } from '@shared/types/game'

export const useGameStore = defineStore('game', () => {
  const socket = ref<Socket | null>(null)

  const roomState = reactive<RoomState>({
    roomId: '',
    platform: 'bilibili',
    currentPuzzle: null,
    streak: 0,
    starLevel: 0,
    highestAffinity: 0,
    guessBoard: [],
    leaderboard: [],
    previousPuzzle: null,
  })

  function connect(platform: string, roomId: string) {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8080'
    socket.value = io(backendUrl)

    socket.value.on('connect', () => {
      roomState.roomId = roomId
      roomState.platform = platform as RoomState['platform']
      socket.value?.emit('room:join', { roomId: roomState.roomId, platform: roomState.platform })
    })

    socket.value.on('game:state', (state: RoomState) => {
      Object.assign(roomState, state)
    })

    socket.value.on('game:newPuzzle', (puzzle: WordPuzzle) => {
      roomState.currentPuzzle = puzzle
    })
  }

  function nextPuzzle() {
    socket.value?.emit('game:nextPuzzle', { roomId: roomState.roomId })
  }

  function disconnect() {
    socket.value?.emit('room:leave', { roomId: roomState.roomId })
    socket.value?.disconnect()
    socket.value = null
  }

  return { socket, roomState, connect, nextPuzzle, disconnect }
})
