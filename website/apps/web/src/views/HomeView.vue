<script setup lang="ts">
import { ref } from 'vue'
import { NICKNAME_MAX, ROOM_CODE_LENGTH, ROUND_SECONDS, ROUNDS_PER_GAME } from '@wtf/shared'
import { myUid, nickname } from '../lib/identity'
import { go } from '../lib/router'

const joinCode = ref('')
const busy = ref(false)
const error = ref<string | null>(null)

async function create(mode: 'solo' | 'private') {
  busy.value = true
  error.value = null
  try {
    const res = await fetch('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, uid: myUid }),
    })
    if (!res.ok) throw new Error()
    const { code } = (await res.json()) as { code: string }
    go(`room/${code}`)
  } catch {
    error.value = '创建房间失败，请稍后重试'
  } finally {
    busy.value = false
  }
}

async function join() {
  const code = joinCode.value.trim().toUpperCase()
  if (code.length !== ROOM_CODE_LENGTH) {
    error.value = `房号是 ${ROOM_CODE_LENGTH} 位字母数字`
    return
  }
  busy.value = true
  error.value = null
  const res = await fetch(`/api/rooms/${code}`).catch(() => null)
  busy.value = false
  if (!res?.ok) {
    error.value = '房间不存在'
    return
  }
  go(`room/${code}`)
}
</script>

<template>
  <header class="hero">
    <h1><span class="glow-cyan">Word</span><span class="glow-pink">To</span>Flush</h1>
    <p class="muted">AI 语义猜词 · 猜得越近，热度越高</p>
  </header>

  <section class="card">
    <p class="title">昵称</p>
    <input v-model="nickname" :maxlength="NICKNAME_MAX" placeholder="给自己起个名字" />
  </section>

  <section class="card cyan modes">
    <button :disabled="busy" @click="create('solo')">🎯 单人练习</button>
    <button class="pink" :disabled="busy" @click="go('match')">⚡ 随机匹配</button>
    <button class="ghost" :disabled="busy" @click="create('private')">🏠 创建房间，邀请好友</button>
    <form class="row" @submit.prevent="join">
      <input
        v-model="joinCode"
        class="grow code"
        :maxlength="ROOM_CODE_LENGTH"
        placeholder="输入房号"
        autocapitalize="characters"
      />
      <button class="ghost" type="submit" :disabled="busy">加入</button>
    </form>
    <p v-if="error" class="glow-pink err">{{ error }}</p>
  </section>

  <section class="card rules">
    <p class="title">玩法</p>
    <ol class="muted">
      <li>每题给出分类和字数，谜底为 1–4 个字。</li>
      <li>输入同样字数的词，AI 给出与谜底的<b>关联度</b>，越热越接近。</li>
      <li>和谜底同一位置的字相同，这个字会被<b>点亮</b>。</li>
      <li>最先猜中的人获胜；每题限时 {{ ROUND_SECONDS }} 秒，一局 {{ ROUNDS_PER_GAME }} 题。</li>
      <li>联机时所有人的猜测实时可见——借鉴对手，抢先一步。</li>
    </ol>
  </section>
</template>

<style scoped>
.hero {
  text-align: center;
  padding: 24px 0 8px;
}
h1 {
  margin: 0;
  font-size: 40px;
  font-weight: 900;
  letter-spacing: 0.02em;
}
.hero p {
  margin: 8px 0 0;
}
.modes {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.code {
  text-transform: uppercase;
  letter-spacing: 0.3em;
}
.err {
  margin: 0;
  font-size: 14px;
}
.rules ol {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
  font-size: 14px;
}
</style>
