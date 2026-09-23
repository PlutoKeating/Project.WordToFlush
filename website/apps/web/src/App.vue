<script setup lang="ts">
import { route } from './lib/router'
import HomeView from './views/HomeView.vue'
import MatchView from './views/MatchView.vue'
import RoomView from './views/RoomView.vue'
</script>

<template>
  <HomeView v-if="route.name === 'home'" />
  <MatchView v-else-if="route.name === 'match'" />
  <!-- key 保证切换房间时重建连接 -->
  <RoomView v-else :key="route.code" :code="route.code" />
</template>
