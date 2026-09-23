// 猜测词清洗，移植自 legacy/backend/app/core/danmaku_filter.py（去掉了仅针对弹幕的口头禅规则）

const EMOJI = /[\u{1F300}-\u{1FAFF}\u{1F1E0}-\u{1F1FF}☀-➿]/gu
const PUNCT = /[\s!！?？。，,.、：:；;…~～（）()【】[\]《》"“”'‘’—\-+=/\\|@#$%^&*·]/g
const CJK_ONLY = /^[一-鿿㐀-䶿豈-﫿]+$/

export type CleanResult = { ok: true; word: string } | { ok: false; reason: string }

export function cleanGuess(raw: string, expectedLength?: number): CleanResult {
  const word = raw.replace(EMOJI, '').replace(PUNCT, '').trim()
  if (!word) return { ok: false, reason: '请输入猜测词' }
  if (!CJK_ONLY.test(word)) return { ok: false, reason: '只能输入汉字' }
  if (expectedLength !== undefined && [...word].length !== expectedLength) {
    return { ok: false, reason: `需要 ${expectedLength} 个字` }
  }
  return { ok: true, word }
}
