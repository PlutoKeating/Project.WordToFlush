// 极简 hash 路由：#/  |  #/room/CODE  |  #/match

import { ref } from 'vue'

export type Route = { name: 'home' } | { name: 'room'; code: string } | { name: 'match' }

function parse(): Route {
  const hash = location.hash.replace(/^#\/?/, '')
  const room = hash.match(/^room\/([A-Za-z0-9]+)$/)
  if (room) return { name: 'room', code: room[1].toUpperCase() }
  if (hash === 'match') return { name: 'match' }
  return { name: 'home' }
}

export const route = ref<Route>(parse())
window.addEventListener('hashchange', () => (route.value = parse()))

export function go(path: string) {
  location.hash = `#/${path}`
}
