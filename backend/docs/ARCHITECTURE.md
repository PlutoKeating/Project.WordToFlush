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
   - 执行 `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. 容器内 API 监听 **8000**，宿主机按 `HOST_BIND_PORT` 映射

## 服务实例化

在 `app/main.py` 模块加载时创建全局单例:

```python
vector_calculator = VectorCalculator()   # Ollama HTTP 客户端 + 缓存
game_master = GameMaster(vector_calculator)  # 业务逻辑
session_manager = SessionManager(game_master)  # 房间管理
connection_manager = ConnectionManager()   # WS 连接管理
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
  → room:join → SessionManager.create_room()
              → ConnectionManager.connect()
              → 回复 game:state

  → game:guess → GameMaster.process_guess()
              → VectorCalculator.calculate_affinity()
              → 检测是否猜中 (affinity >= WIN_AFFINITY_THRESHOLD)
              → ConnectionManager.broadcast(game:guessResult)
              → ConnectionManager.broadcast(game:state)
              → 若猜中: broadcast(game:puzzleSolved)
              → 若猜中: 3s 后自动调用 next_puzzle()

  → game:nextPuzzle → SessionManager.next_puzzle()
                    → ConnectionManager.broadcast(game:newPuzzle)
                    → ConnectionManager.broadcast(game:state)

Client disconnect → ConnectionManager.disconnect()
```

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
    "difficulty": "easy",
    "hints": ["热气腾腾", "多人共享", "麻辣"]
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
| `hints` | string[] | 是 | 提示词列表（用于星级进阶揭示） |

### 添加新分类

在 `app/data/word_data/` 下新建 `<分类名>.json` 文件，按上述格式写入谜题数据即可，无需修改任何业务代码。服务重启后自动生效。
