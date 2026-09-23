<script setup lang="ts">
import { computed } from 'vue'
import { URGENT_SECONDS, type RoomView } from '@wtf/shared'

const props = defineProps<{ state: RoomView; secondsLeft: number | null }>()

const chars = computed(() => {
  const s = props.state
  if (s.answer) return [...s.answer].map((c) => ({ c, on: true, answer: true }))
  const n = s.puzzle?.wordLength ?? 0
  return Array.from({ length: n }, (_, i) => {
    const c = s.revealed[i]
    return { c: c ?? '?', on: !!c, answer: false }
  })
})

const best = computed(() => Math.round(Math.max(0, ...props.state.guesses.map((g) => g.affinity)) * 100))
const urgent = computed(() => props.secondsLeft !== null && props.secondsLeft <= URGENT_SECONDS)
</script>

<template>
  <section class="card pink board">
    <div class="meta">
      <span class="dim">第 {{ state.round }} / {{ state.roundsTotal }} 题</span>
      <span v-if="secondsLeft !== null" :class="urgent ? 'glow-pink' : 'muted'" class="timer">
        {{ secondsLeft }}s
      </span>
    </div>
    <div class="category">分类：{{ state.puzzle?.category ?? '—' }}</div>
    <div class="chars">
      <span
        v-for="(ch, i) in chars"
        :key="i"
        class="char"
        :class="{ on: ch.on, answer: ch.answer }"
      >{{ ch.c }}</span>
    </div>

    <div v-if="state.phase === 'reveal'" class="verdict">
      <span v-if="state.solvedBy" class="glow-cyan">🎉 {{ state.solvedBy }} 猜中了！</span>
      <span v-else class="glow-pink">⏰ 无人猜中</span>
    </div>
    <div v-else class="muted small">
      当前最高关联度 <b class="glow-pink">{{ best }}%</b>
      <span v-if="state.previousAnswer" class="dim"> · 上题：{{ state.previousAnswer }}</span>
    </div>
  </section>
</template>

<style scoped>
.board {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.meta {
  width: 100%;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.timer {
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.category {
  color: var(--purple);
  font-weight: 700;
  letter-spacing: 0.2em;
}
.chars {
  display: flex;
  gap: 10px;
}
.char {
  width: 56px;
  height: 64px;
  display: grid;
  place-items: center;
  font-size: 34px;
  font-weight: 900;
  border-radius: 12px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--ink-3);
  transition: all 0.4s;
}
.char.on {
  color: var(--cyan);
  border-color: var(--cyan);
  text-shadow: 0 0 12px var(--cyan);
}
.char.answer {
  transform: scale(1.08);
  color: var(--green);
  border-color: var(--green);
  text-shadow: 0 0 12px var(--green);
}
.verdict {
  font-weight: 800;
  font-size: 18px;
}
.small {
  font-size: 14px;
}
</style>
