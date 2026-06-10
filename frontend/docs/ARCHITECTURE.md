# Frontend 架构

## 目录结构

```text
frontend/
├── src/
│   ├── main.ts                      # Vue 应用入口 (createPinia)
│   ├── App.vue                      # 根组件 (URL 参数解析 + 连接)
│   ├── env.d.ts                     # Vite 环境变量类型声明
│   ├── components/
│   │   ├── TopBar.vue               # 顶部: 赛季/星级/换题按钮
│   │   ├── DecryptZone.vue          # 中部: 分类/掩码/关联度
│   │   ├── GuessList.vue            # 左侧: 竞猜榜 (按关联度排序)
│   │   └── Leaderboard.vue          # 右侧: 积分榜 (按总分排序)
│   ├── stores/
│   │   └── gameStore.ts             # Pinia store (WebSocket + 状态)
│   └── styles/
│       └── main.css                 # TailwindCSS + 全局样式
├── electron/
│   ├── main.js                      # Electron 单窗口入口
│   └── multi.js                     # Electron 三窗口入口
├── vite.config.ts                   # Vite 构建配置
├── tailwind.config.js               # TailwindCSS 主题
├── tsconfig.json
├── package.json
├── .env.example
└── index.html
```

## 通信流程

```text
App.vue (onMounted)
  → 解析 URL 参数 (platform, roomId)
    → gameStore.connect(platform, roomId)
      → new WebSocket(ws://<backend>/ws)

WebSocket.onopen:
  → send({ event: "room:join", data: { roomId, platform } })

WebSocket.onmessage:
  → game:state     → Object.assign(roomState, msg.data)
  → game:newPuzzle → roomState.currentPuzzle = msg.data

用户点击换题:
  TopBar → gameStore.nextPuzzle()
    → ws.send({ event: "game:nextPuzzle", data: { roomId } })
```

## 组件树

```text
App.vue
├── TopBar.vue         (读取 roomState.streak, starLevel, 触发 nextPuzzle)
├── DecryptZone.vue    (读取 roomState.currentPuzzle, highestAffinity)
├── GuessList.vue      (读取 roomState.guessBoard, 按 affinity 排序)
└── Leaderboard.vue    (读取 roomState.leaderboard, 按 totalScore 排序)
```

## 状态管理

`gameStore.ts` (Pinia setup store):

```typescript
ws: Ref<WebSocket | null>          // WebSocket 连接实例
roomState: RoomState (reactive)    // 房间完整状态

connect(platform, roomId)          // 建立 WebSocket 连接
nextPuzzle()                       // 请求下一题
disconnect()                       // 断开连接
```

## 样式约定

- 布局比例: `aspect-ratio: 9/16`, 最大宽度 480px (竖屏直播适配)
- 颜色体系: TailwindCSS 自定义主题
  - `primary`: #ff6b6b (红色强调)
  - `secondary`: #4ecdc4 (青色)
  - `dark`: #1a1a2e (深色背景)
  - `accent`: #e94560 (玫红)
