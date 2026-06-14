# WordToFlush 架构文档

## 系统分层

```text
┌──────────────────────────────────────────────────────┐
│                    Live Platforms                     │
│        抖音直播间 · 快手直播间 · B站直播间               │
└────────────────────────┬─────────────────────────────┘
                         │ 弹幕数据
┌────────────────────────▼─────────────────────────────┐
│                 Live Driver SDK                       │
│   抖音驱动器(WSS) · 快手驱动器(Web) · B站驱动器(bili)     │
│              → 统一弹幕抽象接口 IDanmakuDriver          │
└────────────────────────┬─────────────────────────────┘
                         │ 标准化弹幕消息
┌────────────────────────▼─────────────────────────────┐
│               Core Server (backend/)                  │
│  ┌──────────────────────────────────────────────┐    │
│  │  FastAPI REST API  │  WebSocket (/ws)         │    │
│  │  GET /health       │  room:join / room:leave  │    │
│  │  GET /api/rooms    │  game:nextPuzzle         │    │
│  │  POST .../next-puzzle                        │    │
│  └──────────┬──────────────┬────────────────────┘    │
│             │              │                          │
│  ┌──────────▼──────────────▼────────────────────┐    │
│  │          SessionManager                      │    │
│  │   全局会话 · 状态管理                │    │
│  └──────────┬───────────────────────────────────┘    │
│             │                                          │
│  ┌──────────▼──────────┐  ┌────────────────────┐     │
│  │     GameMaster      │  │  VectorCalculator  │     │
│  │  发题/判定/结算/排行  │  │  Ollama 语义嵌入   │     │
│  └──────────┬──────────┘  └────────┬───────────┘     │
│             │                       │                  │
│  ┌──────────▼───────────────────────▼───────────┐    │
│  │              Redis Cache                      │    │
│  │    状态持久化 · 弹幕队列 · 嵌入缓存              │    │
│  └───────────────────────────────────────────────┘    │
└────────────────────────┬─────────────────────────────┘
                         │ WebSocket 广播 (game:state)
┌────────────────────────▼─────────────────────────────┐
│              Frontend Clients (frontend/)              │
│  浏览器窗口 · Electron 窗口 · OBS 窗口捕获              │
│  Vue 3 + Pinia + TailwindCSS + 原生 WebSocket         │
└──────────────────────────────────────────────────────┘
```

## 模块边界

| 模块 | 目录 | 技术栈 | 部署方式 |
|------|------|--------|----------|
| 后端 | `backend/` | Python 3.12, FastAPI, uvicorn | Docker Compose (唯一方式) |
| 管理面板 | `backend/admin/` | Python 3.12, Flask, waitress | Docker Compose (与后端同容器) |
| 前端 | `frontend/` | Vue 3, Vite, Pinia, TailwindCSS | npm run dev (本地开发) |
| 共享 | `shared/` | TypeScript 类型定义 | 被前端 import 引用 |

## 通信协议

### REST API (backend/)

- `GET /health` — 健康检查
- `GET /api/rooms` — 列出活跃会话
- `POST /api/next-puzzle` — 触发发题

API 文档自动生成: 启动后访问 `http://localhost:8000/docs` (Swagger UI)

### WebSocket 协议 (JSON over WebSocket)

所有客户端（前端游戏页面、Admin 弹幕桥）连接到同一全局会话 `global`，共享游戏状态。

客户端 → 服务端:
```json
{"event": "room:join",      "data": {"roomId": "global", "platform": "bilibili"}}
{"event": "room:leave",     "data": {}}
{"event": "game:guess",     "data": {"userId": "...", "userName": "...", "guess": "..."}}
{"event": "game:nextPuzzle","data": {}}
```

服务端 → 客户端:
```json
{"event": "game:state",     "data": <RoomState>}
{"event": "game:newPuzzle", "data": <WordPuzzle>}
```

所有 JSON 字段使用 camelCase (通过 Pydantic `to_camel` alias generator 自动转换)。

## 环境变量

### backend/.env

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COMPOSE_PROJECT_NAME` | `word-to-flush-backend` | Docker Compose 项目名 |
| `HOST_BIND_PORT` | `8000` | 宿主机映射端口 (容器内固定 8000) |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API 地址 |
| `OLLAMA_MODEL` | `bge-large-zh` | 嵌入模型名称 |
| `REDIS_URL` | `redis://redis:6379` | Redis 连接地址 |

### frontend/.env

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_DEV_SERVER_PORT` | `3000` | Vite 开发服务器端口 |
| `VITE_BACKEND_URL` | `http://localhost:8000` | 后端 API 地址 |

## 数据模型

所有数据模型定义在:
- 后端: `backend/app/models/game.py` (Pydantic)
- 前端/共享: `shared/types/game.ts` (TypeScript)
- 前后端字段名通过 camelCase 对齐

核心模型: `RoomState`, `WordPuzzle`, `GuessRecord`, `Player`
