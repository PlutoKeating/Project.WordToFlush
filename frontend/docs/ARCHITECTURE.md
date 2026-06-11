# Frontend 架构

## 目录结构

```text
frontend/
├── src/
│   ├── main.ts                      # Vue 应用入口 (createPinia)
│   ├── App.vue                      # 根组件 (URL 参数解析 + 连接)
│   ├── env.d.ts                     # Vite 环境变量类型声明
│   ├── components/
│   │   ├── TopBar.vue               # 顶部: 赛季/换题按钮
│   │   ├── DecryptZone.vue          # 中部: 分类/掩码/关联度/猜中揭示
│   │   ├── GuessList.vue            # 左侧: 竞猜榜 (词汇去重, 按准确率排序)
│   │   ├── GuessInput.vue           # 中部: 猜词输入/结果反馈/猜中弹窗
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
  → game:state        → Object.assign(roomState, msg.data)
  → game:newPuzzle    → roomState.currentPuzzle = msg.data
  → game:guessResult  → lastGuessResult = msg.data
  → game:puzzleSolved → puzzleSolved = msg.data (触发 3s 揭示 + 猜中弹窗)

用户输入猜词:
  GuessInput → gameStore.sendGuess(userId, userName, guess)
    → ws.send({ event: "game:guess", data: { roomId, userId, userName, guess } })

用户点击换题:
  TopBar → gameStore.nextPuzzle()
    → ws.send({ event: "game:nextPuzzle", data: { roomId } })
```

## 组件树

```text
App.vue
├── TopBar.vue         (读取 roomState.streak, 触发 nextPuzzle)
├── DecryptZone.vue    (读取 roomState.currentPuzzle, highestAffinity, puzzleSolved)
├── GuessList.vue      (读取 roomState.guessBoard, 按词汇去重 + 准确率排序)
├── GuessInput.vue     (猜词输入 + 触发 sendGuess, 显示 guessResult 和 puzzleSolved 弹窗)
└── Leaderboard.vue    (读取 roomState.leaderboard, 按 totalScore 排序)
```

## 状态管理

`gameStore.ts` (Pinia setup store):

```typescript
ws: Ref<WebSocket | null>          // WebSocket 连接实例
connected: Ref<boolean>            // 连接状态
roomState: RoomState (reactive)    // 房间完整状态
lastGuessResult: Ref<GuessRecord | null>  // 最近一次猜测结果
puzzleSolved: Ref<PuzzleSolvedEvent | null>  // 猜中事件

connect(platform, roomId)          // 建立 WebSocket 连接
sendGuess(userId, userName, guess) // 发送猜词
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
