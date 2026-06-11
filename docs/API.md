# WordToFlush API 文档

## 基础信息

- 后端框架: FastAPI
- 交互式文档: 启动后访问 `http://localhost:8000/docs` (Swagger UI)
- 替代文档: `http://localhost:8000/redoc` (ReDoc)

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

列出所有当前活跃的房间 ID。

**响应示例:**
```json
{"rooms": ["room-102", "room-888"]}
```

---

### `POST /api/rooms/{room_id}/next-puzzle`

为指定房间触发发题。如果房间不存在则自动创建。

**路径参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `room_id` | string | 房间标识符 |

**查询参数:**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `platform` | string | `"bilibili"` | 平台: bilibili / douyin / kuaishou |

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

### 客户端 → 服务端事件

#### `room:join`
加入房间，建立 WebSocket 连接后发送。

```json
{
  "event": "room:join",
  "data": {
    "roomId": "room-102",
    "platform": "bilibili"
  }
}
```

#### `room:leave`
离开房间。

```json
{
  "event": "room:leave",
  "data": {
    "roomId": "room-102"
  }
}
```

#### `game:nextPuzzle`
请求发下一题。

```json
{
  "event": "game:nextPuzzle",
  "data": {
    "roomId": "room-102"
  }
}
```

### 服务端 → 客户端事件

#### `game:state`
完整房间状态广播，加入房间时发送一次，发题时重新广播。

```json
{
  "event": "game:state",
  "data": {
    "roomId": "room-102",
    "platform": "bilibili",
    "currentPuzzle": { ... },
    "streak": 0,
    "highestAffinity": 0.85,
    "guessBoard": [ ... ],
    "leaderboard": [ ... ],
    "previousPuzzle": null,
    "solvedBy": null
  }
}
```

#### `game:newPuzzle`
新题广播，发题时广播给房间内所有客户端。

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
单条猜测结果广播，每次有用户成功猜词后发送。

```json
{
  "event": "game:guessResult",
  "data": {
    "userId": "user-001",
    "userName": "小明",
    "guess": "文具盒",
    "affinity": 0.87,
    "timestamp": 1718000000000
  }
}
```

#### `error`
服务端处理出错时返回，WebSocket 连接不会断开。

```json
{
  "event": "error",
  "data": {
    "message": "处理猜测时出错，请重试"
  }
}
```

#### `game:puzzleSolved`
谜题被猜中时广播，包含谜底和猜中用户名。前端应显示正确答案 3 秒，之后后端自动推进到下一题。

```json
{
  "event": "game:puzzleSolved",
  "data": {
    "word": "铅笔盒",
    "solvedBy": "小明"
  }
}
```

---

## 数据模型

### RoomState

| 字段 | 类型 | 说明 |
|------|------|------|
| `roomId` | string | 房间 ID |
| `platform` | string | 平台: "bilibili" \| "douyin" \| "kuaishou" |
| `currentPuzzle` | WordPuzzle \| null | 当前谜题 |
| `streak` | int | 连胜次数 |
| `highestAffinity` | float | 当前最高关联度 (0.0-1.0) |
| `guessBoard` | GuessRecord[] | 竞猜记录列表 |
| `leaderboard` | Player[] | 积分排行榜 |
| `previousPuzzle` | string \| null | 上一题谜底 |
| `solvedBy` | string \| null | 本轮猜中者用户名 (null 表示未猜中) |

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
| `userName` | string | 用户名 |
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
