import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { RoomState, WordPuzzle } from '@shared/types/game'

export const useGameStore = defineStore('game', () => {
  const ws = ref<WebSocket | null>(null)

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
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws'

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      roomState.roomId = roomId
      roomState.platform = platform as RoomState['platform']
      ws.value?.send(JSON.stringify({
        event: 'room:join',
        data: { roomId, platform },
      }))
    }

    ws.value.onmessage = (event: MessageEvent) => {
      const msg = JSON.parse(event.data)
      if (msg.event === 'game:state') {
        Object.assign(roomState, msg.data)
      } else if (msg.event === 'game:newPuzzle') {
        roomState.currentPuzzle = msg.data
      }
    }
  }

  function nextPuzzle() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        event: 'game:nextPuzzle',
        data: { roomId: roomState.roomId },
      }))
    }
  }

  function disconnect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        event: 'room:leave',
        data: { roomId: roomState.roomId },
      }))
    }
    ws.value?.close()
    ws.value = null
  }

  return { ws, roomState, connect, nextPuzzle, disconnect }
})
