<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { cleanGuess } from '@wtf/shared'
import GuessFeed from '../components/GuessFeed.vue'
import PuzzleBoard from '../components/PuzzleBoard.vue'
import Scoreboard from '../components/Scoreboard.vue'
import { myUid } from '../lib/identity'
import { go } from '../lib/router'
import { useRoom } from '../lib/useRoom'

const props = defineProps<{ code: string }>()
const { state, connected, fatal, toast, secondsLeft, send, showToast } = useRoom(props.code)

const input = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

const isHost = computed(() => state.value?.mode === 'solo' || state.value?.hostUid === myUid)
const multiplayer = computed(() => state.value && state.value.mode !== 'solo')
const shareUrl = computed(() => `${location.origin}/#/room/${props.code}`)

function submit() {
  const s = state.value
  if (!s?.puzzle || s.phase !== 'playing') return
  const r = cleanGuess(input.value, s.puzzle.wordLength)
  if (!r.ok) return showToast(r.reason)
  send({ event: 'game:guess', data: { guess: r.word } })
  input.value = ''
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    showToast('邀请链接已复制')
  } catch {
    showToast(shareUrl.value)
  }
}

// 新一题开始时自动聚焦输入框
watch(
  () => state.value?.puzzle?.id,
  async () => {
    await nextTick()
    inputEl.value?.focus()
  },
)
</script>

<template>
  <header class="row top">
    <button class="ghost back" @click="go('')">←</button>
    <div class="grow">
      <span class="dim">房号</span> <b class="code glow-cyan">{{ code }}</b>
      <span class="dot" :class="{ ok: connected }" />
    </div>
    <button v-if="multiplayer" class="ghost small" @click="copyLink">邀请</button>
  </header>

  <section v-if="fatal" class="card pink center">
    <p>{{ fatal }}</p>
    <button @click="go('')">返回首页</button>
  </section>

  <section v-else-if="!state" class="card center dim">连接中…</section>

  <!-- 等待开局 -->
  <template v-else-if="state.phase === 'lobby'">
    <section class="card cyan center lobby">
      <p class="muted" v-if="state.mode === 'match'">对手正在进入房间，马上开局…</p>
      <template v-else>
        <p class="muted">把房号 <b class="glow-cyan">{{ code }}</b> 或邀请链接发给好友</p>
        <button class="ghost" @click="copyLink">复制邀请链接</button>
        <button v-if="isHost" @click="send({ event: 'game:start' })">开始游戏（{{ state.players.length }} 人）</button>
        <p v-else class="dim">等待房主开始…</p>
      </template>
    </section>
    <Scoreboard :players="state.players" :host-uid="state.hostUid" />
  </template>

  <!-- 一局结束 -->
  <template v-else-if="state.phase === 'finished'">
    <section class="card cyan center">
      <h2>本局结束</h2>
      <p class="muted">最后一题谜底：<b class="glow-cyan">{{ state.answer }}</b></p>
      <p class="winner" v-if="state.players[0]">🏆 {{ state.players[0].name }} · {{ state.players[0].score }} 分</p>
      <div class="row">
        <button v-if="isHost" class="grow" @click="send({ event: 'game:restart' })">再来一局</button>
        <p v-else class="dim grow">等待房主开始下一局…</p>
        <button class="ghost" @click="go('')">返回首页</button>
      </div>
    </section>
    <Scoreboard :players="state.players" :host-uid="state.hostUid" />
  </template>

  <!-- 游戏中 / 揭晓 -->
  <template v-else>
    <PuzzleBoard :state="state" :seconds-left="secondsLeft" />

    <form class="row" @submit.prevent="submit">
      <input
        ref="inputEl"
        v-model="input"
        class="grow guess"
        :placeholder="`输入 ${state.puzzle?.wordLength ?? ''} 个字`"
        :maxlength="8"
        :disabled="state.phase !== 'playing'"
        enterkeyhint="send"
        autocomplete="off"
      />
      <button type="submit" :disabled="state.phase !== 'playing'">猜</button>
    </form>

    <GuessFeed :guesses="state.guesses" />
    <Scoreboard v-if="multiplayer" :players="state.players" :host-uid="state.hostUid" />

    <button
      v-if="isHost && state.phase === 'playing'"
      class="ghost"
      @click="send({ event: 'game:skip' })"
    >
      {{ state.mode === 'solo' ? '放弃，看答案' : '跳过本题' }}
    </button>
  </template>

  <div v-if="toast" class="toast">{{ toast }}</div>
</template>

<style scoped>
.top {
  gap: 12px;
}
.back {
  padding: 8px 14px;
}
.small {
  padding: 8px 14px;
  font-size: 13px;
}
.code {
  letter-spacing: 0.2em;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-left: 6px;
  border-radius: 50%;
  background: var(--pink);
}
.dot.ok {
  background: var(--green);
}
.center {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: stretch;
}
.center p,
.center h2 {
  margin: 0;
}
.winner {
  font-size: 20px;
  font-weight: 800;
}
.guess {
  font-size: 20px;
  letter-spacing: 0.2em;
}
</style>
