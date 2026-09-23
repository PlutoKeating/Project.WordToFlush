# WordToFlush Backend

Python FastAPI 后端服务 + Flask 管理面板，配合 Docker Compose 一键部署。

## 快速开始

```bash
cd backend
cp .env.example .env      # 按需编辑端口 / Ollama 地址 / Admin 登录凭证
docker compose up -d --build
```

> **前置要求**：宿主机 Ollama 必须监听 `0.0.0.0:11434`（默认仅监听 `127.0.0.1`，Docker 容器无法访问）。
> 启动时使用 `OLLAMA_HOST=0.0.0.0:11434 ollama serve`，或配置 systemd 覆盖文件。
> 详见项目根目录 `README.md` 第一节。

启动后:
- API 服务: `http://localhost:<HOST_BIND_PORT>` (默认 8000)
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- 健康检查: `http://localhost:8000/health`
- **Admin 控制面板**: `http://localhost:<ADMIN_HOST_BIND_PORT>` (默认 8001)

## 本地开发 (不使用 Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# 另开终端启动 admin:
python -m admin.run_admin
```

## 环境变量

全部通过 `backend/.env` 配置:

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COMPOSE_PROJECT_NAME` | `word-to-flush-backend` | Docker Compose 项目名 |
| `HOST_BIND_PORT` | `8000` | 宿主机映射端口 (容器内固定 8000) |
| `ADMIN_HOST_BIND_PORT` | `8001` | Admin 控制面板宿主机映射端口 (容器内固定 8001) |
| `ADMIN_USERNAME` | (必填) | Admin 控制面板登录用户名 |
| `ADMIN_PASSWORD` | (必填) | Admin 控制面板登录密码 |
| `FLASK_SECRET_KEY` | (留空自动生成) | Flask 会话加密密钥 |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API 地址 |
| `OLLAMA_MODEL` | `bge-large-zh` | 嵌入模型名称 (推荐) |
| `WIN_AFFINITY_THRESHOLD` | `0.92` | 猜中关联度阈值 (0.0-1.0) |
| `REDIS_URL` | `redis://redis:6379` | Redis 连接地址 |
| `DY_APP_ID` | (空) | 抖音 App ID (可选) |
| `KS_APP_KEY` | (空) | 快手 App Key (可选) |
| `BILI_PROJECT_ID` | (空) | B站项目 ID (可选) |

## Docker 命名规范

| 资源 | 名称 |
|------|------|
| 项目 (COMPOSE_PROJECT_NAME) | `word-to-flush-backend` |
| 镜像 (image) | `word-to-flush-backend:latest` |
| 容器 (container_name) | `word-to-flush-backend` |
| Redis 容器 | `word-to-flush-backend-redis` |
