# Backend 架构

## 目录结构

```text
backend/
├── app/
│   ├── main.py                       # FastAPI 应用入口
│   │   ├── GET  /health              # 健康检查
│   │   ├── GET  /api/rooms           # 列出活跃房间
│   │   ├── POST /api/rooms/{id}/next-puzzle  # 发题
│   │   └── WS   /ws                  # WebSocket 通信
│   ├── config.py                     # 环境变量读取
│   ├── models/
│   │   └── game.py                   # Pydantic 数据模型
│   ├── core/
│   │   ├── game_master.py            # 游戏逻辑 (发题/判定/结算)
│   │   ├── session_manager.py        # 会话管理 (房间隔离)
│   │   ├── vector_calculator.py      # Ollama 向量嵌入 + 相似度
│   │   └── danmaku_filter.py         # 弹幕清洗与校验
│   ├── websocket/
│   │   └── connection_manager.py     # WebSocket 房间管理
│   └── data/
│       ├── word_data/               # 词库JSON数据（每分类一个文件）
│       └── word_puzzle_repository.py # 谜题库加载器（动态扫描JSON）
├── admin/                            # Admin 控制面板 (Flask)
│   ├── app.py                        # Flask 应用 + SSE + 自动猜词桥
│   ├── config.py                     # Admin 环境变量读取
│   ├── auth.py                       # 会话登录认证
│   ├── run_admin.py                  # 多进程启动入口
│   ├── danmaku/
│   │   ├── __init__.py
│   │   ├── proto_reader.py           # 抖音 Protobuf 二进制解析
│   │   ├── douyin.py                 # 抖音 WSS 弹幕采集
│   │   ├── bilibili.py               # B站 弹幕采集
│   │   └── manager.py                # 采集器管理 + SSE 推送
│   │   ├── dy/                       # 抖音采集参考项目 (TypeScript)
│   │   │   └── src/core/            # 原始签名/解析/连接逻辑
│   │   └── bilibili/                 # B站 API 文档
│   │       └── README.md
│   └── templates/
│       ├── login.html                # 登录页面
│       └── dashboard.html            # 控制面板主页
├── Dockerfile
├── docker-compose.yml                # Redis + Backend 编排
├── requirements.txt
├── .env.example
└── .dockerignore
```

## 启动流程

1. **Docker Compose** 读取 `backend/.env` 进行变量替换
2. 启动 **Redis** 容器 (redis:7-alpine)
3. 构建 **Backend** 镜像并启动容器:
   - 基于 `python:3.12-slim`
   - 安装 `requirements.txt` 依赖
   - 调用 `python -m admin.run_admin`
4. admin.run_admin 通过 `multiprocessing.Process` 启动三个子进程:
   - **FastAPI** (主进程): `uvicorn app.main:app` 监听 8000
   - **Flask Admin**: `waitress admin.app:app` 监听 8001
   - **Auto-Guess Bridge**: WebSocket 连接到 FastAPI 后端，监听 puzzle 状态
5. 宿主机按 `HOST_BIND_PORT` 映射 8000, `ADMIN_HOST_BIND_PORT` 映射 8001

## 服务实例化

在 `app/main.py` 模块加载时创建全局单例:

```python
vector_calculator = VectorCalculator()   # Ollama HTTP 客户端 + 缓存
game_master = GameMaster(vector_calculator)  # 业务逻辑
session_manager = SessionManager(game_master)  # 房间管理
connection_manager = ConnectionManager()   # WS 连接管理
```

## Admin 模块架构

```
Admin Dashboard (Flask, port 8001)
├── /login                          # 登录页面 (HTML)
├── /                               # 控制面板 (HTML, 需登录)
├── /api/login (POST)              # 登录认证
├── /api/logout (POST)             # 退出登录
├── /api/status (GET)              # 采集器状态
├── /api/danmaku/start (POST)      # 启动弹幕采集
├── /api/danmaku/stop (POST)       # 停止弹幕采集
├── /api/danmaku/stream (GET)      # SSE 实时弹幕流
├── /api/auto-guess (POST)         # 配置自动猜词
│
└── DanmakuManager (asyncio)
    ├── DouyinCollector     # 抖音 WSS 弹幕采集
    │   ├── HTTP: 获取直播间信息 (live.douyin.com)
    │   ├── HTTP: 获取 IM 信息 (webcast/im/fetch)
    │   └── WSS:  实时弹幕连接 (webcast100-ws-*.douyin.com)
    ├── BilibiliCollector   # B站 WSS 弹幕采集
    │   ├── HTTP: 获取弹幕服务器信息 (api.live.bilibili.com)
    │   └── WSS:  实时弹幕连接
    └── Auto-Guess Bridge   # 自动猜词桥
        └── WSS → FastAPI /ws (game:guess 事件提交)
```

## 核心调用链

### 发题流程

```
POST /api/rooms/{id}/next-puzzle
  → SessionManager.next_puzzle(room_id)
    → GameMaster.next_puzzle(room_state)
      → WordPuzzleRepository.random()
      → 广播 game:newPuzzle + game:state 到房间
```

### WebSocket 通信流

```
Client connect → WS /ws
  → room:join → 提取 roomId + clientId
              → 构造复合键 "{roomId}:{clientId}"
              → SessionManager.create_room(复合键)
              → ConnectionManager.connect(复合键)
              → 回复 game:state (仅当前客户端)

  → game:guess → 通过 roomId + clientId 解析复合键
              → GameMaster.process_guess()
              → 字数匹配校验 (guess 长度必须 == 谜底长度)
              → 逐字位字符比较，匹配则更新 room_state.revealed_chars[i] = True
              → VectorCalculator.calculate_affinity()
              → 检测是否猜中 (affinity >= WIN_AFFINITY_THRESHOLD)
              → ConnectionManager.broadcast(复合键, game:guessResult)
              → ConnectionManager.broadcast(复合键, game:state)
              → 若猜中: broadcast(复合键, game:puzzleSolved)
              → 若猜中: 3s 后自动调用 next_puzzle()

  → game:nextPuzzle → 通过 roomId + clientId 解析复合键
                    → SessionManager.next_puzzle(复合键)
                    → ConnectionManager.broadcast(复合键, game:newPuzzle)
                    → ConnectionManager.broadcast(复合键, game:state)

Client disconnect → ConnectionManager.disconnect()
```

### Admin 弹幕采集 → 自动猜词

```
Admin Dashboard → POST /api/danmaku/start
  → DanmakuManager.start_collector(platform, room)
    → DouyinCollector.start() / BilibiliCollector.start()
      → WSS 连接直播间, 实时接收弹幕
      → 过滤: 仅保留纯中文文本内容
      → _on_danmaku → DanmakuManager._publish_danmaku()
        → SSE 推送到 Dashboard 前端
        → Auto-Guess Bridge:
          → 检查是否开启自动猜词
          → 字数匹配校验 (与当前谜底字数一致)
          → WSS → FastAPI /ws 发送 game:guess

Auto-Guess Bridge → 维持 WSS 连接到 FastAPI
  → 监听 game:state 获取当前谜底字数
  → 将弹幕用户+内容组装为 game:guess 事件提交
```

### 会话隔离机制

- **前端会话标识**: 每次页面加载生成唯一 `clientId`（`crypto.randomUUID()`），包含在 `room:join` 及后续所有 WebSocket 消息中
- **复合房间键**: 后端使用 `{roomId}:{clientId}` 作为内部房间键，实现每个浏览器页面独立游戏状态
- **刷新/新标签页**: 新的 `clientId` → 新的复合键 → 全新游戏，无状态残留
- **向后兼容**: 若未提供 `clientId`，回退到使用原始 `roomId`

## 数据持久化

- 房间状态: 当前为**内存存储** (Python dict in `SessionManager`)
- Redis: 已配置在 docker-compose 中，待后续集成用于:
  - 会话状态持久化 (多副本)
  - 弹幕队列削峰
  - 嵌入向量缓存 (跨请求复用)

## 词库数据格式

谜题数据存储在 `app/data/word_data/` 目录，每个分类一个 JSON 文件。文件名即为分类名（如 `美食.json`），启动时由 `WordPuzzleRepository` 动态扫描加载。

### JSON 文件格式

每个文件包含一个 JSON 数组，每项为一个谜题对象：

```json
[
  {
    "id": "p001",
    "word": "火锅",
    "wordLength": 2,
    "category": "美食",
    "difficulty": "easy"
  }
]
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 谜题唯一标识 |
| `word` | string | 是 | 谜底（1-4 个中文字符） |
| `wordLength` | int | 是 | 谜底字数 |
| `category` | string | 否* | 分类名（*字段存在但会被文件名覆盖） |
| `difficulty` | string | 是 | 难度：`easy` / `medium` / `hard` |

### 添加新分类

在 `app/data/word_data/` 下新建 `<分类名>.json` 文件，按上述格式写入谜题数据即可，无需修改任何业务代码。服务重启后自动生效。
