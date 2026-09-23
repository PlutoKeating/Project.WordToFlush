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
   - **Auto-Guess Bridge**: WebSocket 连接到 FastAPI 后端，全量转发弹幕为 game:guess
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
    │   ├── HTTP: 房间号解析 — room/v1/Room/get_info 短号→真实ID
    │   ├── HTTP: 获取 buvid3 cookie (www.bilibili.com)
    │   ├── HTTP: 获取 Wbi 签名密钥 (x/web-interface/nav)
    │   ├── HTTP: 获取弹幕服务器 token + host_list (getDanmuInfo)
    │   └── WSS:  实时弹幕连接
    │       ├── protover=3 auth (brotli 压缩) + buvid 字段
    │       ├── heartbeat 30s ({} body)
    │       └── 数据包自愈解析 (逐字节跳过畸形数据)
    └── Auto-Guess Bridge   # 自动猜词桥 (全量转发弹幕)
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
  → room:join → 固定使用全局房间键 "global"
              → 首次加入: SessionManager.create_room("global")
                         → SessionManager.next_puzzle("global")
                         → 广播 game:newPuzzle + game:state
              → 后续加入: 仅向新客户端发送当前 game:state
              → ConnectionManager.connect(websocket, "global")

  → game:guess → 直接路由到 "global" 全局会话
              → GameMaster.process_guess()
              → 字数匹配校验 (guess 长度必须 == 谜底长度)
              → 逐字位字符比较，匹配则更新 room_state.revealed_chars[i] = True
              → VectorCalculator.calculate_affinity()
              → 检测是否猜中 (affinity >= WIN_AFFINITY_THRESHOLD)
              → ConnectionManager.broadcast("global", game:guessResult)
              → ConnectionManager.broadcast("global", game:state)
              → 若猜中: broadcast("global", game:puzzleSolved)
              → 若猜中: 3s 后自动调用 next_puzzle()

  → game:nextPuzzle → SessionManager.next_puzzle("global")
                    → ConnectionManager.broadcast("global", game:newPuzzle)
                    → ConnectionManager.broadcast("global", game:state)

Client disconnect → ConnectionManager.disconnect()
```

### Admin 弹幕采集 → 自动猜词

```
Admin Dashboard → POST /api/danmaku/start
  → DanmakuManager.start_collector(platform, room)
    → DouyinCollector.start() / BilibiliCollector.start()
      → WSS 连接直播间, 实时接收弹幕 (protover=3 brotli 压缩)
      → 启动前: 房间号解析 + buvid3 反爬初始化 + Wbi 签名
      → 过滤: 仅保留非空文本内容 (无 CJK 限制，全量捕获)
      → logger.info 记录每条弹幕 (用户名+内容)
      → _on_danmaku → DanmakuManager._publish_danmaku()
        → SSE 推送到 Dashboard 前端
        → Auto-Guess Bridge (_schedule_bridge_guess):
          → 检查是否开启自动猜词
          → 无冷却限制，每条弹幕即时转发
          → 全量转发弹幕内容作为 game:guess 事件
          → WSS → FastAPI /ws

Bridge 启动顺序:
  run_admin.py → 创建 threading.Event
    → bridge 线程: start_auto_guess_bridge() → set_auto_guess_callback() → Event.set()
    → 主线程: Event.wait(10s) → 确保回调已注册 → 启动 Flask

Backend process_guess():
  → danmaku_filter.clean_danmaku() 清洗 (去表情/标点/非CJK)
  → 字数校验 (长度 == 谜底字数，不符合的静默丢弃)
  → 语义计算 + 判定 + 广播
```

### 会话隔离机制 (已移除)

旧版本使用复合键 `{roomId}:{clientId}` 实现每个浏览器页面的独立游戏状态。
当前版本已移除 clientId 隔离机制，改为全局唯一会话 `global`：
- 所有前端页面连接到同一全局会话
- 所有 clientId 参数从 WebSocket 协议中移除
- 同一时刻只有一场游戏，所有页面同步显示相同状态

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
