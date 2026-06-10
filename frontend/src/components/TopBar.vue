<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed } from 'vue'

const store = useGameStore()

const starDisplay = computed(() => {
  const max = 5
  return '★'.repeat(store.roomState.starLevel) + '☆'.repeat(max - store.roomState.starLevel)
})

const connStatus = computed(() => {
  if (!store.connected) return { text: '未连接', color: 'text-red-500' }
  return { text: '已连接', color: 'text-green-500' }
})

function requestNextPuzzle() {
  store.nextPuzzle()
}
</script>

<template>
  <div class="flex items-center justify-between px-4 py-2 bg-dark/80 border-b border-gray-700">
    <div class="flex items-center gap-2">
      <span class="text-sm text-gray-400">
        赛季 {{ store.roomState.streak > 0 ? 'S' + store.roomState.streak : 'S1' }}
      </span>
      <span :class="['text-xs', connStatus.color]">● {{ connStatus.text }}</span>
    </div>
    <div class="text-lg text-yellow-400">
      {{ starDisplay }}
    </div>
    <div class="flex gap-2">
      <button
        class="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition"
        @click="requestNextPuzzle"
      >
        换题
      </button>
    </div>
  </div>
</template>
