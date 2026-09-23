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
  if (affinity >= 0.85) return 'text-neon-green glow-cyan'
  if (affinity >= 0.5) return 'text-neon-yellow'
  return 'text-ink-muted'
}
</script>

<template>
  <div class="card-neon-purple p-3 flex flex-col min-h-0">
    <h3 class="text-xs text-neon-purple font-bold mb-2 text-center tracking-wider">竞猜榜</h3>
    <div class="flex-1 overflow-y-auto min-h-0">
      <TransitionGroup name="guess-list" tag="div">
        <div
          v-for="item in groupedGuesses"
          :key="item.guess"
          class="flex items-center justify-between text-xs py-1.5 border-b border-edge-light last:border-0"
        >
          <span class="text-ink-dark truncate flex-1 font-medium">{{ item.guess }}</span>
          <span v-if="item.count > 1" class="text-ink-muted ml-0.5">x{{ item.count }}</span>
          <span v-else class="text-ink-muted truncate ml-0.5">{{ item.userName }}</span>
          <span :class="['ml-1 tabular-nums font-bold', affinityColor(item.maxAffinity)]">
            {{ Math.round(item.maxAffinity * 100) }}%
          </span>
        </div>
      </TransitionGroup>
      <div v-if="groupedGuesses.length === 0" class="text-xs text-ink-muted text-center py-4">
        暂无竞猜
      </div>
    </div>
  </div>
</template>

<style scoped>
.guess-list-enter-active {
  transition: all 0.35s ease;
}
.guess-list-enter-from {
  opacity: 0;
  transform: translateX(-16px);
}
</style>
