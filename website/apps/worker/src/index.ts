// Worker 入口路由。生产环境前端经 Pages Functions 的 Service Binding 同源转发到这里，
// 因此浏览器只接触 wtf.plutokeating.beer，Worker 自身域名不暴露给前端代码。

import { NICKNAME_MAX, type CreateRoomRequest } from '@wtf/shared'
import type { Env } from './env'
import { createRoom, isRoomCode, roomStub } from './rooms'

export { GameRoom } from './room'
export { Matchmaker } from './matchmaker'

const UID_RE = /^[A-Za-z0-9_-]{8,64}$/

function json(data: unknown, status = 200, headers: HeadersInit = {}) {
  return Response.json(data, { status, headers })
}

function corsHeaders(request: Request, env: Env): Record<string, string> {
  const origin = request.headers.get('Origin')
  const allowed = env.ALLOWED_ORIGINS.split(',').map((s) => s.trim())
  if (!origin || !allowed.includes(origin)) return {}
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    Vary: 'Origin',
  }
}

/** 规范化身份参数，返回转发给 DO 的查询串；非法时返回 null */
function identity(url: URL): URLSearchParams | null {
  const uid = url.searchParams.get('uid') ?? ''
  if (!UID_RE.test(uid)) return null
  const name =
    [...(url.searchParams.get('name') ?? '').trim()].slice(0, NICKNAME_MAX).join('') ||
    `玩家${uid.slice(0, 4)}`
  return new URLSearchParams({ uid, name })
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url)
    const cors = corsHeaders(request, env)
    const origin = request.headers.get('Origin')

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors })
    // 浏览器请求必须来自白名单来源（WebSocket 不受 CORS 保护，需显式校验）
    if (origin && !cors['Access-Control-Allow-Origin']) return new Response('forbidden', { status: 403 })

    const path = url.pathname

    if (path === '/api/health') return json({ status: 'ok' }, 200, cors)

    if (path === '/api/rooms' && request.method === 'POST') {
      const body = (await request.json().catch(() => ({}))) as Partial<CreateRoomRequest>
      const mode = body.mode === 'solo' ? 'solo' : 'private'
      return json({ code: await createRoom(env, mode) }, 200, cors)
    }

    const roomInfo = path.match(/^\/api\/rooms\/([^/]+)$/)
    if (roomInfo && request.method === 'GET') {
      const code = roomInfo[1].toUpperCase()
      if (!isRoomCode(code)) return json({ error: '房号格式不正确' }, 400, cors)
      const res = await roomStub(env, code).fetch('https://room/info')
      if (!res.ok) return json({ error: '房间不存在' }, 404, cors)
      return json(await res.json(), 200, cors)
    }

    const roomWs = path.match(/^\/ws\/room\/([^/]+)$/)
    if (roomWs) {
      const code = roomWs[1].toUpperCase()
      const params = identity(url)
      if (!isRoomCode(code) || !params) return new Response('bad request', { status: 400 })
      return roomStub(env, code).fetch(`https://room/connect?${params}`, request)
    }

    if (path === '/ws/match') {
      const params = identity(url)
      if (!params) return new Response('bad request', { status: 400 })
      const stub = env.MATCHMAKER.get(env.MATCHMAKER.idFromName('global'))
      return stub.fetch(`https://match/?${params}`, request)
    }

    return new Response('not found', { status: 404, headers: cors })
  },
} satisfies ExportedHandler<Env>
