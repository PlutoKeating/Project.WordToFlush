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
│       └── word_puzzle_repository.py # 谜题库
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
