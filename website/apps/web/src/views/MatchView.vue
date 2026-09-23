<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { MATCH_FULL_PLAYERS, type MatchServerMessage } from '@wtf/shared'
import { wsUrl } from '../lib/identity'
import { go } from '../lib/router'

const count = ref(0)
const startsAt = ref<number | null>(null)
const failed = ref(false)
const now = ref(Date.now())
const ticker = setInterval(() => (now.value = Date.now()), 500)

let matched = false
const ws = new WebSocket(wsUrl('/ws/match'))
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data) as MatchServerMessage
  if (msg.event === 'match:waiting') {
    count.value = msg.data.count
    startsAt.value = msg.data.startsAt
  } else if (msg.event === 'match:found') {
    matched = true
    go(`room/${msg.data.code}`)
  }
}
ws.onclose = () => {
  if (!matched) failed.value = true
}

const countdown = computed(() =>
  startsAt.value ? Math.max(0, Math.ceil((startsAt.value - now.value) / 1000)) : null,
)

onUnmounted(() => {
  clearInterval(ticker)
  ws.close()
})
</script>

<template>
  <section class="card pink wait">
    <div class="spinner" />
    <template v-if="!failed">
      <h2>正在匹配对手…</h2>
      <p class="muted">
        队列中 <b class="glow-cyan">{{ count }}</b> / {{ MATCH_FULL_PLAYERS }} 人
      </p>
      <p class="dim" v-if="countdown !== null">{{ countdown }} 秒后开局</p>
      <p class="dim" v-else>至少 2 人即可开局</p>
    </template>
    <template v-else>
      <h2>匹配连接已断开</h2>
    </template>
    <button class="ghost" @click="go('')">返回首页</button>
  </section>
</template>

<style scoped>
.wait {
  margin-top: 20vh;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
h2 {
  margin: 12px 0 0;
}
p {
  margin: 0;
}
button {
  margin-top: 16px;
}
.spinner {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 4px solid var(--line);
  border-top-color: var(--pink);
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
