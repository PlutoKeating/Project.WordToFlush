// 端到端测试：先 `pnpm dev:worker`（建议 .dev.vars 中 JUDGE_PROVIDER=mock），再 `node apps/worker/test/e2e.mjs`
// 可用 BASE=http://host:port 指定目标

const B = process.env.BASE ?? 'http://localhost:8787'
const W = B.replace(/^http/, 'ws')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function client(path, uid, name) {
  const ws = new WebSocket(`${W}${path}?uid=${uid}&name=${encodeURIComponent(name)}`)
  const c = { ws, state: null, events: [] }
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data)
    c.events.push(m)
    if (m.event === 'room:state') c.state = m.data
  }
  c.send = (m) => ws.send(JSON.stringify(m))
  c.open = new Promise((r) => (ws.onopen = r))
  return c
}

let failed = 0
function check(ok, msg) {
  console.log(ok ? 'ok  ' : 'FAIL', msg)
  if (!ok) failed++
}

const post = (mode, uid) =>
  fetch(`${B}/api/rooms`, { method: 'POST', body: JSON.stringify({ mode, uid }) }).then((r) => r.json())

// ---------- 单人 ----------
const { code } = await post('solo')
const s = client(`/ws/room/${code}`, 'solo-user-0001', '单机')
await s.open
await sleep(400)
check(s.state?.phase === 'playing', 'solo 自动开局')
check(s.state.answer === null && !JSON.stringify(s.state).includes('"word"'), '进行中不下发谜底')
const len = s.state.puzzle.wordLength
s.send({ event: 'game:guess', data: { guess: '天'.repeat(len) } })
await sleep(3000)
check(s.state.guesses.length === 1, '猜测被判定并广播')
const a0 = s.state.guesses[0]?.affinity
check(typeof a0 === 'number' && a0 >= 0 && a0 <= 0.99, `关联度在 [0, 0.99]（${a0}）`)
s.send({ event: 'game:guess', data: { guess: '地'.repeat(len) } })
s.send({ event: 'game:guess', data: { guess: '山'.repeat(len) } })
await sleep(300)
check(s.events.some((m) => m.event === 'error' && m.data.message.includes('太快')), '冷却限流生效')
await sleep(1500)
s.send({ event: 'game:guess', data: { guess: '地'.repeat(len + 1) } })
await sleep(300)
check(s.events.some((m) => m.event === 'error' && m.data.message.includes('个字')), '字数校验')
s.send({ event: 'game:skip' })
await sleep(300)
check(s.state.phase === 'reveal' && typeof s.state.answer === 'string', '放弃后揭晓答案')
await sleep(3500)
check(s.state.phase === 'playing' && s.state.round === 2, '3 秒后 alarm 进入下一题')
s.ws.close()

// ---------- 房号联机 ----------
const { code: pc } = await post('private', 'host-user-0001')
const info = await fetch(`${B}/api/rooms/${pc}`).then((r) => r.json())
check(info.mode === 'private', 'GET /api/rooms/:code')
// 好友先于创建者进入房间，房主仍应是创建者
const b = client(`/ws/room/${pc}`, 'guest-user-001', '客人')
await b.open
await sleep(300)
const a = client(`/ws/room/${pc}`, 'host-user-0001', '房主')
await a.open
await sleep(400)
check(a.state.phase === 'lobby' && a.state.players.length === 2, '私房等待 2 人')
check(a.state.hostUid === 'host-user-0001', '好友抢先入房，创建者仍是房主')
b.send({ event: 'game:start' })
await sleep(300)
check(a.state.phase === 'lobby', '非房主不能开局')
a.send({ event: 'game:start' })
await sleep(400)
check(a.state.phase === 'playing' && b.state.phase === 'playing', '房主开局，双方同步')
a.send({ event: 'game:guess', data: { guess: '人'.repeat(a.state.puzzle.wordLength) } })
await sleep(3000)
check(b.state.guesses.some((g) => g.name === '房主'), '对手的猜测对所有人可见')
a.ws.close()
b.ws.close()

// ---------- 随机匹配 ----------
const ms = [1, 2, 3, 4].map((i) => client('/ws/match', `match-user-000${i}`, `匹配${i}`))
await Promise.all(ms.map((m) => m.open))
await sleep(1000)
const found = ms.map((m) => m.events.find((e) => e.event === 'match:found')?.data.code)
check(found.every((c) => c && c === found[0]), '4 人满员立即成局，同一房号')
const rs = ms.map((_, i) => client(`/ws/room/${found[0]}`, `match-user-000${i + 1}`, `匹配${i + 1}`))
await Promise.all(rs.map((r) => r.open))
await sleep(500)
check(rs[0].state?.phase === 'playing' && rs[0].state.players.length === 4, '全员到齐自动开局')
const late = client(`/ws/room/${found[0]}`, 'late-user-00001', '迟到')
await sleep(800)
check(!late.state, '已开局的匹配房拒绝陌生人')
rs.forEach((r) => r.ws.close())
const two = [5, 6].map((i) => client('/ws/match', `match-user-000${i}`, `匹配${i}`))
await Promise.all(two.map((m) => m.open))
await sleep(500)
const w = two[0].events.filter((e) => e.event === 'match:waiting').pop()
check(w?.data.count === 2 && w.data.startsAt, '2 人排队显示开局倒计时')
two.forEach((m) => m.ws.close())

console.log(failed ? `\n${failed} 项失败` : '\n全部通过')
process.exit(failed ? 1 : 0)
