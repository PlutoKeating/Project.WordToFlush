# WordToFlush Frontend

Vue 3 + Vite 前端客户端，支持浏览器和 Electron 多开。

## 快速开始

```bash
cd frontend
cp .env.example .env      # 按需编辑后端地址
npm install
npm run dev               # 默认 http://localhost:3000
```

## 环境变量

全部通过 `frontend/.env` 配置:

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_DEV_SERVER_PORT` | `3000` | Vite 开发服务器监听端口 |
| `VITE_BACKEND_URL` | `http://localhost:8000` | 后端 API 与 WebSocket 地址 |

## 使用方式

### 浏览器

直接在浏览器打开即可，所有页面共享同一全局游戏会话:

```
http://localhost:3000/
```

### Electron 单窗口

```bash
npm run electron
```

### Electron 多开 (3 窗口)

```bash
npm run electron:multi
```

自动启动 3 个独立 Electron 窗口，可用于多直播间 OBS 推流。所有窗口共享同一游戏状态。

## 依赖

| 依赖 | 用途 |
|------|------|
| Vue 3 | UI 框架 (Composition API) |
| Pinia | 状态管理 (gameStore) |
| TailwindCSS | 原子化 CSS 样式 |
| GSAP | 动画效果 |
| 原生 WebSocket | 与后端实时通信 |

无需 Socket.io 或任何额外 WebSocket 库。
