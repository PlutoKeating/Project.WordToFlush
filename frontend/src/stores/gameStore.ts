import { defineStore } from 'pinia'
import { ref, reactive, watch } from 'vue'
import type { RoomState, WordPuzzle, GuessRecord, PuzzleSolvedEvent } from '@shared/types/game'

const TIMEOUT_SECONDS = 180

export const useGameStore = defineStore('game', () => {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const lastGuessResult = ref<GuessRecord | null>(null)
  const puzzleSolved = ref<PuzzleSolvedEvent | null>(null)
  const timeLeft = ref(TIMEOUT_SECONDS)

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

  let timerHandle: ReturnType<typeof setInterval> | null = null

  function stopTimer() {
    if (timerHandle !== null) {
      clearInterval(timerHandle)
      timerHandle = null
    }
  }

  function startTimer() {
    stopTimer()
    timeLeft.value = TIMEOUT_SECONDS
    timerHandle = setInterval(() => {
      timeLeft.value -= 1
      if (timeLeft.value <= 0) {
        stopTimer()
        nextPuzzle()
      }
    }, 1000)
  }

  watch(() => roomState.currentPuzzle, (newPuzzle) => {
    if (newPuzzle) {
      startTimer()
    } else {
      stopTimer()
    }
  })

  watch(puzzleSolved, (solved) => {
    if (solved) {
      stopTimer()
    }
  })

  function connect() {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws'

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
      ws.value?.send(JSON.stringify({
        event: 'room:join',
        data: { roomId: 'global', platform: 'bilibili' },
      }))
    }

    ws.value.onmessage = (event: MessageEvent) => {
      const msg = JSON.parse(event.data)
      if (msg.event === 'game:state') {
        const data = msg.data
        Object.assign(roomState, data)
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
        data: { userId, userName, guess: guess.trim() },
      }))
    }
  }

  function nextPuzzle() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        event: 'game:nextPuzzle',
        data: {},
      }))
    }
  }

  function disconnect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        event: 'room:leave',
        data: {},
      }))
    }
    ws.value?.close()
    ws.value = null
    connected.value = false
  }

  return { ws, connected, roomState, lastGuessResult, puzzleSolved, timeLeft, connect, sendGuess, nextPuzzle, disconnect }
})
