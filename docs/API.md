# WordToFlush API 文档

## 基础信息

- 后端框架: FastAPI
- 管理面板: Flask (Admin 控制面板)
- 交互式文档: 启动后访问 `http://localhost:8000/docs` (Swagger UI)
- 替代文档: `http://localhost:8000/redoc` (ReDoc)
- Admin 面板: `http://localhost:<ADMIN_HOST_BIND_PORT>` (默认 8001)

---

## REST API

### `GET /health`

健康检查端点，返回服务运行状态。

**响应示例:**
```json
{"status": "ok"}
```

---

### `GET /api/rooms`

列出当前活跃的全局会话。

**响应示例:**
```json
{"rooms": ["global"]}
```

---

### `POST /api/next-puzzle`

触发发题。系统使用全局唯一会话（`global`），首次调用自动创建会话。

**响应示例:**
```json
{
  "status": "ok",
  "puzzle": {
    "id": "p001",
    "word": "笔记本",
    "wordLength": 3,
    "category": "学习用品",
    "difficulty": "easy"
  }
}
```

---

## WebSocket API

**端点:** `ws://<host>:8000/ws`

所有客户端（前端页面、Admin 弹幕桥）连接到此同一端点，共享全局唯一游戏会话 `global`。

### 客户端 → 服务端事件

#### `room:join`
加入全局会话。所有客户端加入同一会话，共享游戏状态。

```json
{
  "event": "room:join",
  "data": {
    "roomId": "global",
    "platform": "bilibili"
  }
}
```

#### `room:leave`
离开全局会话。

```json
{
  "event": "room:leave",
  "data": {}
}
```

#### `game:guess`
发送猜测词。弹幕桥和前端测试输入均使用此事件。**字数校验由后端 `process_guess` 自动完成**——长度与谜底不符的猜测会被静默丢弃。

```json
{
  "event": "game:guess",
  "data": {
    "userId": "danmaku-12345",
    "userName": "小明",
    "guess": "文具盒"
  }
}
```

#### `game:nextPuzzle`
请求发下一题。

```json
{
  "event": "game:nextPuzzle",
  "data": {}
}
```

### 服务端 → 客户端事件

#### `game:state`
完整游戏状态广播。发题时、猜词时广播给所有已连接客户端。

```json
{
  "event": "game:state",
  "data": {
    "roomId": "global",
    "platform": "bilibili",
    "currentPuzzle": { "id": "p001", "word": "笔记本", "wordLength": 3, "category": "学习用品", "difficulty": "easy" },
    "streak": 0,
    "highestAffinity": 0.85,
    "guessBoard": [
      { "userId": "danmaku-12345", "userName": "小明", "guess": "文具盒", "affinity": 0.87, "timestamp": 1718000000000 }
    ],
    "leaderboard": [
      { "userId": "danmaku-12345", "userName": "小明", "totalScore": 87, "currentScore": 87, "guessCount": 1 }
    ],
    "previousPuzzle": null,
    "solvedBy": null,
    "revealedChars": [false, false, false]
  }
}
```

#### `game:newPuzzle`
新题广播。

```json
{
  "event": "game:newPuzzle",
  "data": {
    "id": "p002",
    "word": "铅笔盒",
    "wordLength": 3,
    "category": "学习用品",
    "difficulty": "easy"
  }
}
```

#### `game:guessResult`
单条猜测结果广播，每次成功处理猜测后发送。

```json
{
  "event": "game:guessResult",
  "data": {
    "userId": "danmaku-12345",
    "userName": "小明",
    "guess": "文具盒",
    "affinity": 0.87,
    "timestamp": 1718000000000
  }
}
```

#### `game:puzzleSolved`
谜题被猜中时广播。

```json
{
  "event": "game:puzzleSolved",
  "data": {
    "word": "铅笔盒",
    "solvedBy": "小明"
  }
}
```

#### `error`
服务端处理出错时返回。

```json
{
  "event": "error",
  "data": {
    "message": "处理猜测时出错，请重试"
  }
}
```

---

## 数据模型

### RoomState

| 字段 | 类型 | 说明 |
|------|------|------|
| `roomId` | string | 固定为 `"global"` |
| `platform` | string | 平台标识 |
| `currentPuzzle` | WordPuzzle \| null | 当前谜题 |
| `streak` | int | 连胜次数 |
| `highestAffinity` | float | 当前最高关联度 (0.0-1.0) |
| `guessBoard` | GuessRecord[] | 竞猜记录列表 |
| `leaderboard` | Player[] | 积分排行榜 |
| `previousPuzzle` | string \| null | 上一题谜底 |
| `solvedBy` | string \| null | 本轮猜中者用户名 |
| `revealedChars` | boolean[] | 逐字位揭示状态 |

### WordPuzzle

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 谜题 ID |
| `word` | string | 谜底 |
| `wordLength` | int | 字数 |
| `category` | string | 分类 |
| `difficulty` | string | 难度: "easy" \| "medium" \| "hard" |

### GuessRecord

| 字段 | 类型 | 说明 |
|------|------|------|
| `userId` | string | 用户 ID |
| `userName` | string | 用户名（弹幕来源显示真实观众名） |
| `guess` | string | 猜测词 |
| `affinity` | float | 关联度 (0.0-1.0) |
| `timestamp` | int | Unix 毫秒时间戳 |

### Player

| 字段 | 类型 | 说明 |
|------|------|------|
| `userId` | string | 用户 ID |
| `userName` | string | 用户名 |
| `totalScore` | int | 总分 |
| `currentScore` | int | 当前轮得分 |
| `guessCount` | int | 猜测次数 |

---

## Admin API

Admin 控制面板 API，运行在端口 8001（容器内）。

### `POST /api/login`

登录认证。

**请求体:**
```json
{"username": "admin", "password": "xxx"}
```

**响应示例:**
```json
{"ok": true}
```

### `POST /api/logout`

退出登录。

### `GET /api/status`

获取采集器状态和自动猜词配置。

**响应示例:**
```json
{
  "collectors": [
    {"platform": "douyin", "room": "123456", "running": true, "connected": true, "error": ""}
  ],
  "autoGuess": {"enabled": true}
}
```

### `POST /api/danmaku/start`

启动指定平台的弹幕采集。采集器抓取**所有非空文本弹幕**（不限字数、不限制 CJK），通过自动猜词桥全量发送到后端。每条弹幕按用户做 1 秒冷却，同一用户 1 秒内多条弹幕仅转发第一条。

**请求体:**
```json
{
  "platform": "douyin",
  "room": "123456"
}
```

### `POST /api/danmaku/stop`

停止指定平台的弹幕采集。

**请求体:**
```json
{"platform": "douyin", "room": "123456"}
```

### `POST /api/auto-guess`

控制自动猜词开关。

**请求体:**
```json
{
  "enabled": true
}
```

### `GET /api/danmaku/stream`

SSE 实时弹幕流（EventSource 协议）。

**事件格式:**
```json
{
  "platform": "douyin",
  "room": "123456",
  "userName": "小明",
  "content": "文具盒",
  "timestamp": 1718000000000
}
```

---

## 核心数据流

```
直播间弹幕 → 平台采集器(DouyinCollector/BilibiliCollector)
    → 过滤: 仅保留非空文本内容 (无 CJK 限制，全量捕获)
    → logger.info 记录每条弹幕 (用户名+内容)
    → DanmakuManager._publish_danmaku()
        ├─→ SSE 推送 (Admin Dashboard 实时展示)
        └─→ Auto-Guess Bridge (_schedule_bridge_guess)
            → 自动猜词开关检查
            → 按用户 1s 冷却去重 (同用户多条弹幕仅首条送入)
            → WebSocket game:guess 事件 → FastAPI Backend (/ws)
                → danmaku_filter.clean_danmaku() 清洗 (去表情/标点/非CJK)
                → 字数校验 (长度必须 == 谜底字数)
                → VectorCalculator.calculate_affinity() Ollama 语义计算
                → 猜中判定 (affinity >= WIN_AFFINITY_THRESHOLD)
                → 广播 game:guessResult + game:state + game:puzzleSolved
                    → 所有连接的前端页面同步更新
```

### 启动顺序保证

`run_admin.py` 使用 `threading.Event` 确保 Auto-Guess Bridge 回调已在 `DanmakuManager` 注册后（10s timeout）才启动 Flask 服务，消除采集器先于 Bridge 启动导致弹幕丢失的竞态窗口。
