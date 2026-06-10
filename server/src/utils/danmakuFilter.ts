export interface CleanedDanmaku {
  valid: boolean
  word: string
  reason?: string
}

const FILLER_PATTERNS = [
  /那我猜/i,
  /[!！]{2,}/,
  /[0-9]{2,}$/,
  /^[?？]{2,}$/,
  /^[。，.]+$/,
  /^[哈嘿哎啊哦嗯呀诶嗨哟噢]*$/,
  /^[emEm]{2,}$/,
  /^\d+$/,
]

const EMOTICON_REGEX =
  /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u
const PUNCT_REGEX = /[!！?？。，,\.、：:；;…~～（）()【】\[\]《》""''""''—\-+=\/\|\\@#$%^&*◇◆○●◎☆★△▲▽▼□■▷▶◁◀…·‥¨´]/

export function cleanDanmaku(raw: string): CleanedDanmaku {
  let text = raw.trim()

  text = text.replace(EMOTICON_REGEX, '')

  text = text.normalize('NFKC')

  text = text.replace(PUNCT_REGEX, '')

  for (const pattern of FILLER_PATTERNS) {
    text = text.replace(pattern, '').trim()
  }

  if (text.length === 0) {
    return { valid: false, word: '', reason: 'empty after cleaning' }
  }

  const CJK_RANGE = /^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]{2,4}$/
  if (!CJK_RANGE.test(text)) {
    return { valid: false, word: text, reason: 'contains non-CJK after cleaning' }
  }

  if (text.length < 2 || text.length > 4) {
    return { valid: false, word: text, reason: `length ${text.length} out of [2,4]` }
  }

  return { valid: true, word: text }
}
