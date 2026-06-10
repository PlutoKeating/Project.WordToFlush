<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed } from 'vue'

const store = useGameStore()

const maskedWord = computed(() => {
  const puzzle = store.roomState.currentPuzzle
  if (!puzzle) return '? '.repeat(3).trim()
  return '? '.repeat(puzzle.wordLength).trim()
})

const category = computed(() => {
  return store.roomState.currentPuzzle?.category || '等待发题'
})

const highestAffinity = computed(() => {
  return Math.round(store.roomState.highestAffinity * 100)
})

const availableHints = computed(() => {
  const puzzle = store.roomState.currentPuzzle
  if (!puzzle) return []
  return puzzle.hints.slice(0, store.roomState.starLevel)
})

const hintLabel = computed(() => {
  if (store.roomState.starLevel === 0) return '猜对加星解锁提示'
  return `已解锁 ${store.roomState.starLevel} 条提示`
})
</script>

<template>
  <div class="flex-1 flex flex-col items-center justify-center p-6 text-center">
    <div class="text-lg text-secondary mb-2">{{ category }}</div>
    <div class="text-4xl font-bold tracking-widest mb-4 text-primary">
      {{ maskedWord }}
    </div>
    <div class="text-sm text-gray-400 mb-3">
      当前最高关联度：<span class="text-green-400 font-bold">{{ highestAffinity }}%</span>
    </div>

    <div class="text-xs text-gray-500 mb-2">{{ hintLabel }}</div>
    <div v-if="availableHints.length > 0" class="flex flex-wrap gap-2 justify-center mb-3">
      <span
        v-for="(hint, i) in availableHints"
        :key="i"
        class="px-2 py-0.5 text-xs rounded bg-gray-800 text-secondary border border-gray-700"
      >
        {{ hint }}
      </span>
    </div>

    <div v-if="store.roomState.previousPuzzle" class="mt-2 text-xs text-gray-600">
      上期谜底：<span class="text-gray-500">{{ store.roomState.previousPuzzle }}</span>
    </div>
  </div>
</template>
