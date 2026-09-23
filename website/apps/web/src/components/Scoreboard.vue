<script setup lang="ts">
import type { PlayerView } from '@wtf/shared'
import { myUid } from '../lib/identity'

defineProps<{ players: PlayerView[]; hostUid: string | null }>()
</script>

<template>
  <section class="card">
    <p class="title">积分榜</p>
    <ol>
      <li v-for="(p, i) in players" :key="p.uid" :class="{ me: p.uid === myUid, off: !p.online }">
        <span class="rank">{{ i + 1 }}</span>
        <span class="name">
          {{ p.name }}<template v-if="p.uid === hostUid"> 👑</template><template v-if="p.uid === myUid"> (我)</template>
        </span>
        <span class="dim best">本题 {{ Math.round(p.roundBest * 100) }}%</span>
        <span class="score glow-cyan">{{ p.score }}</span>
      </li>
    </ol>
  </section>
</template>

<style scoped>
ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}
li.me .name {
  color: var(--cyan);
}
li.off {
  opacity: 0.45;
}
.rank {
  width: 20px;
  color: var(--ink-3);
  font-weight: 800;
}
.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.best {
  font-size: 12px;
}
.score {
  font-weight: 800;
  min-width: 36px;
  text-align: right;
}
</style>
