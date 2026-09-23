export interface Env {
  AI: Ai
  JUDGE_CACHE: KVNamespace
  ROOM: DurableObjectNamespace
  MATCHMAKER: DurableObjectNamespace
  /** 逗号分隔的允许来源，例如 https://wtf.plutokeating.beer,http://localhost:5173 */
  ALLOWED_ORIGINS: string
  /** Jev 主通道：'workers-ai' | 'typesafe' */
  JEV_PROVIDER: string
  /** 可选：TypeSafe 直连备用通道，用 `wrangler secret put TYPESAFE_API_KEY` 设置 */
  TYPESAFE_API_KEY?: string
}
