// 匿名身份：首次访问生成 uid，昵称可修改，均保存在 localStorage（不可用时退化为内存）

import { ref, watch } from 'vue'
import { NICKNAME_MAX } from '@wtf/shared'

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* 隐私模式等场景忽略 */
  }
}

let uid = read('wtf.uid')
if (!uid) {
  uid = crypto.randomUUID()
  write('wtf.uid', uid)
}

export const myUid = uid
export const nickname = ref(read('wtf.name') ?? `玩家${uid.slice(0, 4)}`)

watch(nickname, (v) => write('wtf.name', [...v.trim()].slice(0, NICKNAME_MAX).join('')))

export function identityQuery() {
  return new URLSearchParams({ uid: myUid, name: nickname.value.trim() }).toString()
}

export function wsUrl(path: string) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}${path}?${identityQuery()}`
}
