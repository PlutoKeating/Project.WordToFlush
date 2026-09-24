import { ROOM_CODE_LENGTH, type RoomMode } from '@wtf/shared'
import type { Env } from './env'

// 去掉易混淆字符 0/O/1/I/L
const ALPHABET = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'

function randomCode(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(ROOM_CODE_LENGTH))
  return [...bytes].map((b) => ALPHABET[b % ALPHABET.length]).join('')
}

export function roomStub(env: Env, code: string) {
  return env.ROOM.get(env.ROOM.idFromName(code))
}

export async function createRoom(
  env: Env,
  mode: RoomMode,
  opts: { expectedPlayers?: number; hostUid?: string } = {},
): Promise<string> {
  for (let attempt = 0; attempt < 5; attempt++) {
    const code = randomCode()
    const res = await roomStub(env, code).fetch('https://room/init', {
      method: 'POST',
      body: JSON.stringify({ code, mode, ...opts }),
    })
    if (res.ok) return code
  }
  throw new Error('无法分配房号')
}

export function isRoomCode(code: string) {
  return new RegExp(`^[${ALPHABET}]{${ROOM_CODE_LENGTH}}$`).test(code)
}
