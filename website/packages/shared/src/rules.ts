// 游戏规则常量：前端展示与 Worker 判定共用，改动需同步文档 website/API.md

export const ROUND_SECONDS = 180
/** 倒计时最后 N 秒前端标红 */
export const URGENT_SECONDS = 18
/** 猜中 / 超时后展示答案的时长 */
export const REVEAL_SECONDS = 3
export const ROUNDS_PER_GAME = 5
export const MIN_WORD_LENGTH = 1
export const MAX_WORD_LENGTH = 4

export const MAX_PLAYERS = 8
/** 随机匹配：凑满此人数立即开局 */
export const MATCH_FULL_PLAYERS = 4
/** 随机匹配：等待超过此秒数且至少 MATCH_MIN_PLAYERS 人即开局 */
export const MATCH_WAIT_SECONDS = 30
export const MATCH_MIN_PLAYERS = 2

/** 同一玩家两次猜测的最小间隔 */
export const GUESS_COOLDOWN_MS = 1500

/** 计分：猜中者得分；其余玩家按本轮最高关联度得安慰分（最高关联度% / 10，向下取整） */
export const SOLVE_POINTS = 100

export const NICKNAME_MAX = 12
export const ROOM_CODE_LENGTH = 6
