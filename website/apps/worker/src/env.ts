export interface Env {
  AI: Ai
  ROOM: DurableObjectNamespace
  MATCHMAKER: DurableObjectNamespace
  /** 逗号分隔的允许来源，例如 https://wtf.plutokeating.beer,http://localhost:5173 */
  ALLOWED_ORIGINS: string
  /** 判定通道：'workers-ai'（默认）| 'mock'（仅本地开发） */
  JUDGE_PROVIDER?: string
}
