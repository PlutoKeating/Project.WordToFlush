// 语义判定器：Workers AI `@cf/baai/bge-m3` 词向量 + 余弦相似度（免费额度内，无需密钥）。
// - 关联度：按谜底各自的底噪 baseline 归一化，(cos - baseline) / (TOP - baseline)，截断到 [0, 0.99]
// - 猜中：与谜底或其别名 aliases 字面相同（向量无法可靠区分同义词与强相关词）
// - 向量缓存在 DO 内存中，谜底向量每题只算一次，热门猜测词跨题复用
// baseline 由题库离线校准：谜底与 20 个无关参照词的平均余弦，改模型后需重新生成。

import type { Env } from './env'
import type { Puzzle } from './puzzles'

export interface Verdict {
  /** 0..1，用于热力条 */
  affinity: number
  /** 猜中 */
  solved: boolean
}

const MODEL = '@cf/baai/bge-m3'
/** 近义词在 bge-m3 上的典型余弦值，作为 100% 的参照点 */
const TOP = 0.85
const CACHE_MAX = 2000

const vectors = new Map<string, number[]>()

function remember(text: string, vec: number[]) {
  if (vectors.size >= CACHE_MAX) vectors.delete(vectors.keys().next().value!)
  vectors.set(text, vec)
}

async function embedWorkersAi(env: Env, texts: string[]): Promise<number[][]> {
  const res = (await env.AI.run(MODEL, { text: texts })) as { data?: number[][] }
  if (!res.data || res.data.length !== texts.length) throw new Error('bge-m3 响应缺少 data')
  return res.data
}

/** 仅本地开发（.dev.vars 设置 JUDGE_PROVIDER=mock）：按字符生成伪向量，不联网 */
async function embedMock(_env: Env, texts: string[]): Promise<number[][]> {
  return texts.map((t) => {
    const v = new Array<number>(64).fill(0.1)
    for (const ch of t) v[ch.charCodeAt(0) % 64] += 1
    return v
  })
}

async function embed(env: Env, texts: string[]): Promise<Map<string, number[]>> {
  const missing = [...new Set(texts.filter((t) => !vectors.has(t)))]
  if (missing.length) {
    const call = env.JUDGE_PROVIDER === 'mock' ? embedMock : embedWorkersAi
    const vecs = await call(env, missing)
    missing.forEach((t, i) => remember(t, vecs[i]))
  }
  return new Map(texts.map((t) => [t, vectors.get(t)!]))
}

function cosine(a: number[], b: number[]) {
  let dot = 0
  let na = 0
  let nb = 0
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i]
    na += a[i] * a[i]
    nb += b[i] * b[i]
  }
  return na && nb ? dot / Math.sqrt(na * nb) : 0
}

export async function judge(env: Env, puzzle: Puzzle, guess: string): Promise<Verdict> {
  if (guess === puzzle.word || puzzle.aliases?.includes(guess)) return { affinity: 1, solved: true }

  const vec = await embed(env, [puzzle.word, guess])
  const raw = cosine(vec.get(puzzle.word)!, vec.get(guess)!)
  // 旧版本存档的谜底没有 baseline，用题库中位数兜底
  const base = puzzle.baseline ?? 0.466
  const affinity = Math.min(0.99, Math.max(0, (raw - base) / (TOP - base)))
  return { affinity, solved: false }
}
