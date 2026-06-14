<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { computed, ref, watch } from 'vue'

const store = useGameStore()

const showAnswer = ref(false)
const answerText = ref('')

watch(() => store.puzzleSolved, (solved) => {
  if (solved) {
    answerText.value = solved.word
    showAnswer.value = true
    setTimeout(() => {
      showAnswer.value = false
    }, 3000)
  }
})

watch(() => store.roomState.currentPuzzle, () => {
  showAnswer.value = false
})

const puzzleChars = computed(() => {
  const puzzle = store.roomState.currentPuzzle
  if (!puzzle) return Array(3).fill('?')
  return puzzle.word.split('')
})

const revealedChars = computed(() => {
  return store.roomState.revealedChars || []
})

const category = computed(() => {
  return store.roomState.currentPuzzle?.category || '等待发题'
})

const highestAffinity = computed(() => {
  return Math.round(store.roomState.highestAffinity * 100)
})

const countdownText = computed(() => {
  const t = store.timeLeft
  const m = String(Math.floor(t / 60)).padStart(2, '0')
  const s = String(t % 60).padStart(2, '0')
  return `${m}:${s}`
})

const isCountdownUrgent = computed(() => {
  return store.timeLeft <= 18
})

const hasPuzzle = computed(() => {
  return store.roomState.currentPuzzle !== null
})
</script>

<template>
  <div class="card-neon-pink px-5 py-4 flex flex-col items-center gap-3">
    <div class="text-base text-neon-purple font-bold tracking-[0.25em] uppercase">
      分类：{{ category }}
    </div>
    <div class="text-4xl font-black tracking-[0.3em] flex gap-3">
      <span
        v-for="(char, i) in puzzleChars"
        :key="i"
        :class="[
          'transition-all duration-500 inline-block',
          showAnswer
            ? 'text-neon-cyan scale-125 glow-cyan'
            : revealedChars[i]
              ? 'text-neon-cyan glow-cyan'
              : 'text-ink-muted',
        ]"
      >
        {{ showAnswer ? char : revealedChars[i] ? char : '?' }}
      </span>
    </div>
    <div class="text-sm text-ink-gray">
      当前最高关联度：
      <span class="text-neon-pink font-bold glow-pink">{{ highestAffinity }}%</span>
    </div>
    <div v-if="hasPuzzle" class="text-sm font-bold" :class="isCountdownUrgent ? 'text-neon-pink glow-pink' : 'text-ink-gray'">
      倒计时：{{ countdownText }}
    </div>
    <div v-if="store.roomState.previousPuzzle" class="text-xs text-ink-muted">
      上期谜底：<span class="text-ink-gray">{{ store.roomState.previousPuzzle }}</span>
    </div>
  </div>
</template>
