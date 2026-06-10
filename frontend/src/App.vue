<script setup lang="ts">
import TopBar from './components/TopBar.vue'
import DecryptZone from './components/DecryptZone.vue'
import GuessList from './components/GuessList.vue'
import Leaderboard from './components/Leaderboard.vue'
import { useGameStore } from './stores/gameStore'
import { onMounted } from 'vue'

const store = useGameStore()

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  const platform = params.get('platform') || 'bilibili'
  const roomId = params.get('roomId') || 'default'
  store.connect(platform, roomId)
})
</script>

<template>
  <div class="w-full h-full flex flex-col bg-dark" style="aspect-ratio: 9/16; max-width: 480px; margin: 0 auto;">
    <TopBar />
    <DecryptZone />
    <div class="flex-1 flex overflow-hidden">
      <GuessList class="w-1/3" />
      <div class="w-1/3 flex items-center justify-center">
        <!-- 动态特效区 -->
        <div class="text-secondary text-sm opacity-50">特效区</div>
      </div>
      <Leaderboard class="w-1/3" />
    </div>
  </div>
</template>
