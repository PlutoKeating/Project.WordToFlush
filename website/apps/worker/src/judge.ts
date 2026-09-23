// 语义判定器：一次 Jev 调用同时得到「关联度（score）」与「是否同一事物（noul）」。
// 通道由 JEV_PROVIDER 指定主通道，另一个可用时作为备用：
// - workers-ai：Workers AI binding（typesafe/jev），无需密钥，但按 AI Gateway 统一计费，需预充值 credits
// - typesafe：TypeSafe 直连，需 `wrangler secret put TYPESAFE_API_KEY`（新账号赠 $5 额度）
// 结果以 (谜底 id, 猜测词) 为键缓存在 KV，保证同词同分、热门词不重复计费。

import type { Env } from './env'

export interface Verdict {
  /** 0..1，用于热力条 */
  affinity: number
  /** 猜中 */
  solved: boolean
}

/** 修改评分标准必须同时递增版本号，使旧缓存失效 */
const RUBRIC_VERSION = 'v1'
const SAME_THRESHOLD = 0.9

// 10 级有序量表，score 返回 0..9 的概率加权均值
const AFFINITY_LEVELS = [
  '毫无关系',
  '极弱的联想',
  '属于同一大领域',
  '同一类别但差别很大',
  '有明显联系',
  '同类且相近的事物',
  '经常一起出现或被一起提及',
  '高度相关，或互为上下位词',
  '近义词',
  '同一事物',
]

function buildRequest(answer: string, category: string, guess: string) {
  return {
    state: { 谜底: answer, 分类: category, 猜测词: guess },
    questions: {
      affinity: {
        type: 'score',
        instructions: '按普通中文使用者的直觉，判断猜测词与谜底在语义上的关联程度。',
        criteria: AFFINITY_LEVELS,
      },
      same: {
        type: 'noul',
        instructions: '猜测词与谜底是否指同一事物（同义词、常见别称也算）？',
      },
    },
  }
}

interface JevAnswers {
  affinity?: { score?: number }
  same?: { noul?: number }
}

function parseAnswers(raw: unknown): JevAnswers {
  // Workers AI 与 TypeSafe 直连的外层信封不同，统一向内找 answers
  let node: any = raw
  for (let i = 0; i < 3 && node && !node.answers; i++) node = node.result
  if (!node?.answers) throw new Error(`Jev 响应缺少 answers: ${JSON.stringify(raw).slice(0, 300)}`)
  return node.answers as JevAnswers
}

function toVerdict(answers: JevAnswers): Verdict {
  const score = answers.affinity?.score
  const same = answers.same?.noul
  if (typeof score !== 'number' || typeof same !== 'number') {
    throw new Error(`Jev 响应字段异常: ${JSON.stringify(answers).slice(0, 300)}`)
  }
  const affinity = Math.min(1, Math.max(0, score / (AFFINITY_LEVELS.length - 1)))
  return { affinity, solved: same >= SAME_THRESHOLD }
}

async function callWorkersAi(env: Env, body: ReturnType<typeof buildRequest>): Promise<Verdict> {
  const raw = await env.AI.run('typesafe/jev' as any, body as any)
  return toVerdict(parseAnswers(raw))
}

async function callTypeSafe(env: Env, body: ReturnType<typeof buildRequest>): Promise<Verdict> {
  const res = await fetch('https://api.typesafe.ai/v1/systemone', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.TYPESAFE_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model: 'jev-latest', ...body }),
  })
  if (!res.ok) throw new Error(`TypeSafe HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`)
  return toVerdict(parseAnswers(await res.json()))
}

/** 仅本地开发（.dev.vars 设置 JEV_PROVIDER=mock）：按共同字数 + 哈希噪声给出伪分数，不联网 */
async function callMock(_env: Env, body: ReturnType<typeof buildRequest>): Promise<Verdict> {
  const { 谜底: answer, 猜测词: guess } = body.state
  const shared = [...guess].filter((c) => answer.includes(c)).length / answer.length
  const hash = [...(answer + guess)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7)
  return { affinity: Math.min(0.95, shared * 0.6 + (hash % 300) / 1000), solved: false }
}

export async function judge(
  env: Env,
  puzzle: { id: string; word: string; category: string },
  guess: string,
): Promise<Verdict> {
  if (guess === puzzle.word) return { affinity: 1, solved: true }

  const key = `judge:${RUBRIC_VERSION}:${puzzle.id}:${guess}`
  const cached = await env.JUDGE_CACHE.get<Verdict>(key, 'json')
  if (cached) return cached

  const body = buildRequest(puzzle.word, puzzle.category, guess)
  const providers =
    env.JEV_PROVIDER === 'mock'
      ? [callMock]
      : env.JEV_PROVIDER === 'typesafe'
        ? [callTypeSafe, callWorkersAi]
        : [callWorkersAi, callTypeSafe]
  if (!env.TYPESAFE_API_KEY && providers.includes(callTypeSafe)) providers.splice(providers.indexOf(callTypeSafe), 1)

  let verdict: Verdict | null = null
  let lastErr: unknown
  for (const call of providers) {
    try {
      verdict = await call(env, body)
      break
    } catch (err) {
      console.warn(`Jev 通道 ${call.name} 失败`, err)
      lastErr = err
    }
  }
  if (!verdict) throw lastErr

  await env.JUDGE_CACHE.put(key, JSON.stringify(verdict))
  return verdict
}
