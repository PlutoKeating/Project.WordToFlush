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
</script>

<template>
  <div class="flex-1 flex flex-col items-center justify-center p-6 text-center">
    <div class="text-lg text-secondary mb-2">{{ category }}</div>
    <div class="text-4xl font-bold mb-4 flex justify-center gap-3">
      <span
        v-for="(char, i) in puzzleChars"
        :key="i"
        :class="[
          'transition-all duration-300',
          showAnswer ? 'text-green-400 scale-110' : revealedChars[i] ? 'text-green-400' : 'text-primary',
        ]"
      >
        {{ showAnswer ? char : revealedChars[i] ? char : '?' }}
      </span>
    </div>
    <div class="text-sm text-gray-400 mb-3">
      当前最高关联度：<span class="text-green-400 font-bold">{{ highestAffinity }}%</span>
    </div>

    <div v-if="store.roomState.previousPuzzle" class="mt-2 text-xs text-gray-600">
      上期谜底：<span class="text-gray-500">{{ store.roomState.previousPuzzle }}</span>
    </div>
  </div>
</template>
