<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed } from 'vue'

const store = useGameStore()

interface GuessGroup {
  guess: string
  maxAffinity: number
  userName: string
  count: number
}

const groupedGuesses = computed(() => {
  const map = new Map<string, GuessGroup>()
  for (const record of store.roomState.guessBoard) {
    const existing = map.get(record.guess)
    if (existing) {
      existing.count += 1
      if (record.affinity > existing.maxAffinity) {
        existing.maxAffinity = record.affinity
        existing.userName = record.userName
      }
    } else {
      map.set(record.guess, {
        guess: record.guess,
        maxAffinity: record.affinity,
        userName: record.userName,
        count: 1,
      })
    }
  }

  return [...map.values()]
    .sort((a, b) => b.maxAffinity - a.maxAffinity)
    .slice(0, 10)
})

function affinityColor(affinity: number): string {
  if (affinity >= 0.85) return 'text-green-400'
  if (affinity >= 0.5) return 'text-yellow-400'
  return 'text-gray-500'
}
</script>

<template>
  <div class="p-2 overflow-y-auto">
    <h3 class="text-xs text-gray-500 mb-2 text-center">竞猜榜</h3>
    <TransitionGroup name="guess-list" tag="div">
      <div
        v-for="item in groupedGuesses"
        :key="item.guess"
        class="flex items-center justify-between text-xs py-1 border-b border-gray-800"
      >
        <span class="text-gray-300 truncate flex-1">{{ item.guess }}</span>
        <span v-if="item.count > 1" class="text-gray-600 ml-1">x {{ item.count }}</span>
        <span v-else class="text-gray-500 truncate ml-1">{{ item.userName }}</span>
        <span :class="['ml-1', affinityColor(item.maxAffinity)]">
          {{ Math.round(item.maxAffinity * 100) }}%
        </span>
      </div>
    </TransitionGroup>
    <div v-if="groupedGuesses.length === 0" class="text-xs text-gray-600 text-center py-4">
      暂无竞猜
    </div>
  </div>
</template>

<style scoped>
.guess-list-enter-active {
  transition: all 0.4s ease;
}
.guess-list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}
</style>
