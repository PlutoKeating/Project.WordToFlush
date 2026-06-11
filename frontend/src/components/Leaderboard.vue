<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed } from 'vue'

const store = useGameStore()

const rankedPlayers = computed(() => {
  return [...store.roomState.leaderboard]
    .sort((a, b) => b.totalScore - a.totalScore)
    .slice(0, 10)
})

function rankGlow(index: number): string {
  if (index === 0) return 'text-neon-yellow font-bold'
  if (index === 1) return 'text-neon-cyan font-bold'
  if (index === 2) return 'text-neon-pink font-bold'
  return 'text-ink-muted'
}
</script>

<template>
  <div class="card-neon-cyan p-3 flex flex-col min-h-0">
    <h3 class="text-xs text-neon-cyan font-bold mb-2 text-center tracking-wider">总积分榜</h3>
    <div class="flex-1 overflow-y-auto min-h-0">
      <TransitionGroup name="lb-list" tag="div">
        <div
          v-for="(player, index) in rankedPlayers"
          :key="player.userId"
          class="flex items-center justify-between text-xs py-1.5 border-b border-edge-light last:border-0"
        >
          <span :class="['w-4 tabular-nums', rankGlow(index)]">{{ index + 1 }}</span>
          <span class="text-ink-dark truncate flex-1 ml-1 font-medium">{{ player.userName }}</span>
          <span class="text-neon-yellow tabular-nums font-bold ml-1">{{ player.totalScore }}</span>
        </div>
      </TransitionGroup>
      <div v-if="rankedPlayers.length === 0" class="text-xs text-ink-muted text-center py-4">
        暂无玩家
      </div>
    </div>
  </div>
</template>

<style scoped>
.lb-list-enter-active {
  transition: all 0.35s ease;
}
.lb-list-enter-from {
  opacity: 0;
  transform: translateX(16px);
}
</style>
