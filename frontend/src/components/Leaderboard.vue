<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed } from 'vue'

const store = useGameStore()

const rankedPlayers = computed(() => {
  return [...store.roomState.leaderboard]
    .sort((a, b) => b.totalScore - a.totalScore)
    .slice(0, 10)
})
</script>

<template>
  <div class="p-2 overflow-y-auto">
    <h3 class="text-xs text-gray-500 mb-2 text-center">总积分榜</h3>
    <div
      v-for="(player, index) in rankedPlayers"
      :key="player.userId"
      class="flex items-center justify-between text-xs py-1 border-b border-gray-800"
    >
      <span class="text-gray-400 w-4">{{ index + 1 }}</span>
      <span class="text-gray-300 truncate flex-1">{{ player.userName }}</span>
      <span class="text-yellow-400 ml-1">{{ player.totalScore }}</span>
    </div>
    <div v-if="rankedPlayers.length === 0" class="text-xs text-gray-600 text-center py-4">
      暂无玩家
    </div>
  </div>
</template>
