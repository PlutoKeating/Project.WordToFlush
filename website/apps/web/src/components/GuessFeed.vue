<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GuessView } from '@wtf/shared'
import { myUid } from '../lib/identity'

const props = defineProps<{ guesses: GuessView[] }>()
const sortBy = ref<'hot' | 'time'>('hot')

// 同一个词合并展示（多人猜过显示 ×N），保留最早猜出者
const rows = computed(() => {
  const map = new Map<string, GuessView & { count: number; mine: boolean }>()
  for (const g of [...props.guesses].reverse()) {
    const e = map.get(g.guess)
    if (e) {
      e.count++
      e.mine ||= g.uid === myUid
      e.ts = Math.max(e.ts, g.ts)
    } else map.set(g.guess, { ...g, count: 1, mine: g.uid === myUid })
  }
  const list = [...map.values()]
  return sortBy.value === 'hot'
    ? list.sort((a, b) => b.affinity - a.affinity)
    : list.sort((a, b) => b.ts - a.ts)
})

function heat(a: number) {
  if (a >= 0.8) return 'var(--green)'
  if (a >= 0.6) return 'var(--cyan)'
  if (a >= 0.4) return 'var(--amber)'
  return 'var(--pink)'
}
</script>

<template>
  <section class="card feed">
    <div class="head">
      <p class="title">竞猜榜</p>
      <div class="tabs">
        <button :class="{ ghost: sortBy !== 'hot' }" @click="sortBy = 'hot'">热度</button>
        <button :class="{ ghost: sortBy !== 'time' }" @click="sortBy = 'time'">最新</button>
      </div>
    </div>
    <p v-if="!rows.length" class="dim empty">还没有人猜，来打响第一枪</p>
    <TransitionGroup tag="ul" name="list">
      <li v-for="r in rows" :key="r.guess" :class="{ mine: r.mine }">
        <div class="bar" :style="{ width: `${Math.round(r.affinity * 100)}%`, background: heat(r.affinity) }" />
        <span class="word">{{ r.guess }}</span>
        <span class="who dim">{{ r.name }}<template v-if="r.count > 1"> ×{{ r.count }}</template></span>
        <span class="pct" :style="{ color: heat(r.affinity) }">{{ Math.round(r.affinity * 100) }}%</span>
      </li>
    </TransitionGroup>
  </section>
</template>

<style scoped>
.feed {
  flex: 1;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.head .title {
  margin: 0;
}
.tabs {
  display: flex;
  gap: 6px;
}
.tabs button {
  padding: 4px 10px;
  font-size: 12px;
}
.empty {
  text-align: center;
  margin: 24px 0;
}
ul {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  max-height: 46vh;
}
li {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--panel-2);
  overflow: hidden;
}
li.mine {
  outline: 1px solid color-mix(in srgb, var(--cyan) 50%, transparent);
}
.bar {
  position: absolute;
  inset: 0 auto 0 0;
  opacity: 0.14;
  transition: width 0.5s;
}
.word {
  font-weight: 800;
  font-size: 17px;
  letter-spacing: 0.1em;
}
.who {
  flex: 1;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pct {
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.list-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.list-enter-active,
.list-move {
  transition: all 0.35s;
}
</style>
