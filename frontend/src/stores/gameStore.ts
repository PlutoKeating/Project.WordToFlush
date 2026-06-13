import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { RoomState, WordPuzzle, GuessRecord, PuzzleSolvedEvent } from '@shared/types/game'

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export const useGameStore = defineStore('game', () => {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const lastGuessResult = ref<GuessRecord | null>(null)
  const puzzleSolved = ref<PuzzleSolvedEvent | null>(null)
  const clientId = ref('')
  const localRoomId = ref('')

  const roomState = reactive<RoomState>({
    roomId: '',
    platform: 'bilibili',
    currentPuzzle: null,
    streak: 0,
    highestAffinity: 0,
    guessBoard: [],
    leaderboard: [],
    previousPuzzle: null,
    solvedBy: null,
    revealedChars: [],
  })

  function connect(platform: string, roomId: string) {
    clientId.value = generateUUID()
    localRoomId.value = roomId

    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws'

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
      roomState.roomId = roomId
      roomState.platform = platform as RoomState['platform']
      ws.value?.send(JSON.stringify({
        event: 'room:join',
        data: { roomId, platform, clientId: clientId.value },
      }))
    }

    ws.value.onmessage = (event: MessageEvent) => {
      const msg = JSON.parse(event.data)
      if (msg.event === 'game:state') {
        const data = msg.data
        const restoredRoomId = roomState.roomId
        Object.assign(roomState, data)
        roomState.roomId = restoredRoomId
      } else if (msg.event === 'game:newPuzzle') {
        roomState.currentPuzzle = msg.data
        puzzleSolved.value = null
      } else if (msg.event === 'game:guessResult') {
        lastGuessResult.value = msg.data as GuessRecord
      } else if (msg.event === 'game:puzzleSolved') {
        puzzleSolved.value = msg.data as PuzzleSolvedEvent
      }
    }

    ws.value.onclose = () => {
      connected.value = false
    }

    ws.value.onerror = () => {
      connected.value = false
    }
  }

  function sendGuess(userId: string, userName: string, guess: string) {
    if (ws.value?.readyState === WebSocket.OPEN && guess.trim()) {
      ws.value.send(JSON.stringify({
        event: 'game:guess',
        data: { roomId: localRoomId.value, userId, userName, guess: guess.trim(), clientId: clientId.value },
      }))
    }
  }

  function nextPuzzle() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        event: 'game:nextPuzzle',
        data: { roomId: localRoomId.value, clientId: clientId.value },
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
    connected.value = false
  }

  return { ws, connected, roomState, lastGuessResult, puzzleSolved, clientId, connect, sendGuess, nextPuzzle, disconnect }
})
