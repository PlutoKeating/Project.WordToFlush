# WordToFlush Website

AI 语义猜词网页游戏：单人练习、约定房号联机、随机匹配。前端部署在 Cloudflare Pages，后端（房间状态 + 判定器）部署在 Cloudflare Worker，语义判定使用 Workers AI 的 `@cf/baai/bge-m3` 词向量（免费额度内，无需密钥）。

## 目录

```
website/
├── apps/
│   ├── web/                 前端 Vue3 + Vite → Pages 项目 wordtoflush-web
│   │   ├── functions/       Pages Functions：/api/* 与 /ws/* 经 Service Binding 转发到 Worker
│   │   ├── src/lib/         身份、hash 路由、房间 WebSocket 连接
│   │   ├── src/views/       首页 / 匹配 / 房间
│   │   └── src/components/  谜题板 / 竞猜榜 / 积分榜
│   └── worker/              后端 → Worker wordtoflush-api
│       └── src/
│           ├── index.ts     路由、来源白名单、身份参数校验
│           ├── room.ts      GameRoom Durable Object（每房号一个，权威状态 + alarm 计时）
│           ├── matchmaker.ts Matchmaker Durable Object（全局匹配队列）
│           ├── judge.ts     判定器：bge-m3 余弦相似度 → 关联度；别名命中 → 猜中
│           ├── puzzles.ts   题库加载
│           ├── data/word_data/  题库 JSON（14 个分类，含 baseline 与 aliases）
│       └── test/e2e.mjs     端到端测试（单人 / 房号 / 匹配）
├── packages/shared/         前后端共享：规则常量、猜测词清洗、协议类型
├── ARCHITECTURE.md
└── API.md
```

## 本地开发

```bash
cd website
pnpm install
cp apps/worker/.dev.vars.example apps/worker/.dev.vars   # 默认 JUDGE_PROVIDER=mock，不联网
pnpm dev:worker    # wrangler dev，:8787
pnpm dev:web       # vite，:5173，/api 与 /ws 代理到 :8787
```

`pnpm typecheck` 对三个包做类型检查；Worker 运行时执行 `node apps/worker/test/e2e.mjs` 做端到端测试（删掉 `.dev.vars` 中的 mock 即测试真实 bge-m3）。

## 部署

推送 `main` 后由 Cloudflare 的 Git 集成自动部署（控制台配置）：

| 项目 | 根目录 | 构建 / 部署命令 | 输出目录 | 监视路径 |
|---|---|---|---|---|
| Worker `wordtoflush-api` | `website` | 部署：`cd apps/worker && npx wrangler deploy` | – | `website/apps/worker/*`、`website/packages/shared/*` |
| Pages `wordtoflush-web` | `website/apps/web` | 构建：`cd ../.. && pnpm install --frozen-lockfile && pnpm build` | `dist` | `website/apps/web/*`、`website/packages/shared/*` |

- Pages 根目录必须是 `website/apps/web`：Functions 目录与输出目录都按根目录解析。
- 该目录下存在 `wrangler.toml`，Pages 以它为准并**忽略控制台中的变量**；构建变量 `SKIP_DEPENDENCY_INSTALL`（跳过 Pages 自带的 npm 安装，它不识别 pnpm workspace）与 `PNPM_VERSION` 写在其 `[vars]` 中。

手动部署：`pnpm deploy:worker`、`pnpm deploy:web`（先 Worker 后 Pages，Pages 的 Service Binding 依赖 Worker）。

- Worker 设置了 `workers_dev: false`，不暴露 `*.workers.dev`；浏览器只访问 Pages 域名。
- 自定义域名在控制台绑定：Pages → `wtf.plutokeating.beer`；Worker → `wtf.williamhvollita.dpdns.org`（可选，仅用于运维排障，不在前端出现）。

### 判定器与题库

- `JUDGE_PROVIDER`：默认走 Workers AI；本地 `.dev.vars` 可设为 `mock`（伪向量，不联网）。
- 题库每项的 `baseline` 由 bge-m3 离线校准；**更换模型必须重新计算全部 baseline**。
- `aliases` 只收录与谜底字数相同的同义词/别称，命中即判猜中；新增谜底时按需补充。
