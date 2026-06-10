<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { ref, watch } from 'vue'

const store = useGameStore()

const userId = ref('player-' + Math.floor(Math.random() * 10000))
const userName = ref('玩家' + Math.floor(Math.random() * 1000))
const guessText = ref('')
const showResult = ref(false)
const resultFlash = ref('')
const showSolvedPopup = ref(false)
const solvedByName = ref('')

watch(() => store.puzzleSolved, (solved) => {
  if (solved) {
    showSolvedPopup.value = true
    solvedByName.value = solved.solvedBy
    setTimeout(() => {
      showSolvedPopup.value = false
    }, 3000)
  }
})

watch(() => store.lastGuessResult, (result) => {
  if (result) {
    showResult.value = true
    const pct = Math.round(result.affinity * 100)
    if (result.affinity >= 0.85) {
      resultFlash.value = 'result-excellent'
    } else if (result.affinity >= 0.5) {
      resultFlash.value = 'result-good'
    } else {
      resultFlash.value = 'result-low'
    }
    setTimeout(() => {
      showResult.value = false
    }, 2000)
  }
})

function submitGuess() {
  if (!guessText.value.trim()) return
  store.sendGuess(userId.value, userName.value, guessText.value)
  guessText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    submitGuess()
  }
}
</script>

<template>
  <div class="p-2 flex flex-col items-center justify-center gap-2 h-full">
    <div class="w-full flex flex-col gap-2">
      <input
        v-model="userName"
        type="text"
        placeholder="昵称"
        maxlength="8"
        class="w-full px-2 py-1 text-xs rounded bg-gray-800 text-gray-300 border border-gray-700 focus:outline-none focus:border-secondary"
      />
      <div class="flex gap-1">
        <input
          v-model="guessText"
          type="text"
          placeholder="输入猜测..."
          maxlength="4"
          @keydown="handleKeydown"
          class="flex-1 px-2 py-1 text-sm rounded bg-gray-800 text-white border border-gray-700 focus:outline-none focus:border-primary"
        />
        <button
          @click="submitGuess"
          class="px-3 py-1 text-xs rounded bg-primary hover:bg-accent text-white transition font-bold"
        >
          猜
        </button>
      </div>
    </div>

    <Transition name="fade">
      <div
        v-if="showSolvedPopup"
        class="text-center px-4 py-3 rounded result-solved animate-pulse"
      >
        <div class="text-lg font-bold text-green-400 mb-1">🎯 猜中了！</div>
        <div class="text-sm text-gray-300">{{ solvedByName }}</div>
      </div>
    </Transition>

    <Transition name="fade">
      <div
        v-if="showResult && store.lastGuessResult && !showSolvedPopup"
        :class="['text-center text-xs px-3 py-1 rounded', resultFlash]"
      >
        <div class="text-gray-300">{{ store.lastGuessResult.guess }}</div>
        <div class="font-bold text-lg">
          {{ Math.round(store.lastGuessResult.affinity * 100) }}%
        </div>
      </div>
    </Transition>

    <div v-if="!showResult && !showSolvedPopup" class="text-xs text-gray-600 text-center">
      输入猜测词测试语义关联
    </div>
  </div>
</template>

<style scoped>
.result-excellent {
  background: rgba(78, 205, 196, 0.2);
  border: 1px solid #4ecdc4;
  color: #4ecdc4;
}
.result-good {
  background: rgba(255, 107, 107, 0.15);
  border: 1px solid #ff6b6b;
  color: #ff6b6b;
}
.result-low {
  background: rgba(128, 128, 128, 0.15);
  border: 1px solid #666;
  color: #999;
}
.result-solved {
  background: rgba(34, 197, 94, 0.15);
  border: 1px solid #22c55e;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
