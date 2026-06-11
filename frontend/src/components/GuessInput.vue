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
  <div class="card-neon-purple px-4 py-3 flex flex-col gap-2.5">
    <div class="flex gap-2">
      <input
        v-model="userName"
        type="text"
        placeholder="昵称"
        maxlength="8"
        class="w-2/5 px-2.5 py-1.5 text-xs rounded bg-cyber-panel text-ink-dark border border-edge-light focus:outline-none focus:border-neon-purple transition-colors"
      />
      <div class="flex-1 flex gap-1.5">
        <input
          v-model="guessText"
          type="text"
          placeholder="输入猜测词..."
          minlength="1"
          maxlength="4"
          @keydown="handleKeydown"
          class="flex-1 px-3 py-1.5 text-xs rounded bg-cyber-panel text-ink-dark border border-edge-light focus:outline-none focus:border-neon-pink transition-colors"
        />
        <button
          @click="submitGuess"
          class="btn-primary text-xs px-4 font-bold"
        >
          猜
        </button>
      </div>
    </div>

    <Transition name="fade">
      <div
        v-if="showSolvedPopup"
        class="rounded-card px-3 py-2 text-center animate-pulse"
        style="background: rgba(0, 214, 180, 0.1); border: 1px solid rgba(0, 230, 118, 0.4); box-shadow: 0 0 10px rgba(0, 230, 118, 0.15);"
      >
        <div class="text-base font-bold text-neon-green glow-cyan mb-0.5">🎯 猜中了！</div>
        <div class="text-xs text-ink-gray">{{ solvedByName }}</div>
      </div>
    </Transition>

    <Transition name="fade">
      <div
        v-if="showResult && store.lastGuessResult && !showSolvedPopup"
        :class="['text-center text-xs px-3 py-2 rounded-card', resultFlash]"
      >
        <div class="text-ink-gray">{{ store.lastGuessResult.guess }}</div>
        <div class="text-base font-bold">
          {{ Math.round(store.lastGuessResult.affinity * 100) }}%
        </div>
      </div>
    </Transition>

    <div v-if="!showResult && !showSolvedPopup" class="text-xs text-ink-muted text-center">
      输入猜测词测试语义关联
    </div>
  </div>
</template>

<style scoped>
.result-excellent {
  background: rgba(0, 230, 118, 0.1);
  border: 1px solid rgba(0, 230, 118, 0.4);
  color: theme('colors.neon-green');
}
.result-good {
  background: rgba(255, 45, 127, 0.08);
  border: 1px solid rgba(255, 45, 127, 0.35);
  color: theme('colors.neon-pink');
}
.result-low {
  background: rgba(136, 136, 160, 0.08);
  border: 1px solid rgba(136, 136, 160, 0.3);
  color: theme('colors.ink-muted');
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
