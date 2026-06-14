<script setup lang="ts">
import TopBar from './components/TopBar.vue'
import DecryptZone from './components/DecryptZone.vue'
import GuessList from './components/GuessList.vue'
import GuessInput from './components/GuessInput.vue'
import Leaderboard from './components/Leaderboard.vue'
import { useGameStore } from './stores/gameStore'
import { onMounted } from 'vue'

const store = useGameStore()

onMounted(() => {
  store.connect()
})
</script>

<template>
  <div class="w-full h-full bg-cyber-bg" style="aspect-ratio: 9/16; max-width: 480px; margin: 0 auto;">
    <div class="h-full flex flex-col p-3 gap-2.5">
      <TopBar />
      <DecryptZone />
      <GuessInput />
      <div class="flex-1 flex gap-2.5 min-h-0">
        <GuessList class="flex-1" />
        <Leaderboard class="flex-1" />
      </div>
    </div>
  </div>
</template>
