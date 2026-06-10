<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed } from 'vue'

const store = useGameStore()

const sortedGuesses = computed(() => {
  return [...store.roomState.guessBoard]
    .sort((a, b) => b.affinity - a.affinity)
    .slice(0, 10)
})
</script>

<template>
  <div class="p-2 overflow-y-auto">
    <h3 class="text-xs text-gray-500 mb-2 text-center">竞猜榜</h3>
    <div
      v-for="(record, index) in sortedGuesses"
      :key="record.userId + record.timestamp"
      class="flex items-center justify-between text-xs py-1 border-b border-gray-800"
    >
      <span class="text-gray-400 truncate flex-1">{{ record.userName }}</span>
      <span class="text-green-400 ml-1">{{ Math.round(record.affinity * 100) }}%</span>
    </div>
    <div v-if="sortedGuesses.length === 0" class="text-xs text-gray-600 text-center py-4">
      暂无竞猜
    </div>
  </div>
</template>
