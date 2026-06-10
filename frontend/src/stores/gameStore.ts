import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { RoomState, WordPuzzle, GuessRecord, PuzzleSolvedEvent } from '@shared/types/game'

export const useGameStore = defineStore('game', () => {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const lastGuessResult = ref<GuessRecord | null>(null)
  const puzzleSolved = ref<PuzzleSolvedEvent | null>(null)

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
    solvedBy: null,
  })

  function connect(platform: string, roomId: string) {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws'

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
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
        data: { roomId: roomState.roomId, userId, userName, guess: guess.trim() },
      }))
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
    connected.value = false
  }

  return { ws, connected, roomState, lastGuessResult, puzzleSolved, connect, sendGuess, nextPuzzle, disconnect }
})
