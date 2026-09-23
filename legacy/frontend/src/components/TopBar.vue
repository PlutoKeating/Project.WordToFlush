<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed } from 'vue'

const store = useGameStore()

const connStatus = computed(() => {
  if (!store.connected) return { text: '未连接', dot: 'bg-neon-pink', glow: '' }
  return { text: '已连接', dot: 'bg-neon-green animate-pulse', glow: 'shadow-neon-green' }
})

function requestNextPuzzle() {
  store.nextPuzzle()
}
</script>

<template>
  <div class="card-neon-cyan px-4 py-2.5 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <span class="text-sm text-neon-cyan font-bold tracking-[0.3em] glow-cyan">
        S{{ store.roomState.streak > 0 ? store.roomState.streak : '1' }}
      </span>
      <div class="flex items-center gap-1.5">
        <span class="inline-block w-2.5 h-2.5 rounded-full" :class="[connStatus.dot, connStatus.glow]"></span>
        <span class="text-xs text-ink-gray">{{ connStatus.text }}</span>
      </div>
    </div>
    <button class="btn-primary text-xs px-4" @click="requestNextPuzzle">
      ⏭ 换题
    </button>
  </div>
</template>
