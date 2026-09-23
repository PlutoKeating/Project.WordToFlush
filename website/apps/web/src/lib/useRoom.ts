// 房间 WebSocket 连接：自动重连、心跳、服务器时钟校正

import { computed, onUnmounted, ref, shallowRef } from 'vue'
import type { ClientMessage, GuessView, RoomView, ServerMessage } from '@wtf/shared'
import { wsUrl } from './identity'

const HEARTBEAT_MS = 25_000
const MAX_RETRIES = 5

export function useRoom(code: string) {
  const state = shallowRef<RoomView | null>(null)
  const connected = ref(false)
  const fatal = ref<string | null>(null)
  const toast = ref<string | null>(null)
  const lastGuess = shallowRef<GuessView | null>(null)
  /** 服务器时间 - 本地时间 */
  const clockOffset = ref(0)
  const now = ref(Date.now())

  let ws: WebSocket | null = null
  let retries = 0
  let closedByUs = false
  let heartbeat: ReturnType<typeof setInterval> | undefined
  let toastTimer: ReturnType<typeof setTimeout> | undefined
  const ticker = setInterval(() => (now.value = Date.now()), 250)

  function showToast(msg: string) {
    toast.value = msg
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => (toast.value = null), 2500)
  }

  function open() {
    ws = new WebSocket(wsUrl(`/ws/room/${code}`))
    ws.onopen = () => {
      connected.value = true
      retries = 0
      heartbeat = setInterval(() => send({ event: 'ping' }), HEARTBEAT_MS)
    }
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data) as ServerMessage
      if (msg.event === 'room:state') {
        clockOffset.value = msg.data.now - Date.now()
        state.value = msg.data
      } else if (msg.event === 'game:guessResult') {
        lastGuess.value = msg.data
      } else if (msg.event === 'error') {
        showToast(msg.data.message)
      }
    }
    ws.onclose = (e) => {
      connected.value = false
      clearInterval(heartbeat)
      if (closedByUs) return
      if (e.code === 4000) {
        fatal.value = '你已在其他窗口进入此房间'
        return
      }
      // 从未收到状态就断开：房间不存在 / 已满 / 已开局
      if (!state.value && retries >= 1) {
        fatal.value = '无法加入房间（可能已满或已开局）'
        return
      }
      if (retries++ < MAX_RETRIES) setTimeout(open, 1000 * retries)
      else fatal.value = '连接已断开，请刷新重试'
    }
  }

  function send(msg: ClientMessage) {
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg))
  }

  const secondsLeft = computed(() => {
    const d = state.value?.deadline
    if (!d) return null
    return Math.max(0, Math.ceil((d - (now.value + clockOffset.value)) / 1000))
  })

  open()
  onUnmounted(() => {
    closedByUs = true
    clearInterval(ticker)
    clearInterval(heartbeat)
    ws?.close()
  })

  return { state, connected, fatal, toast, lastGuess, secondsLeft, send, showToast }
}
