# WordToFlush Website

AI 语义猜词网页游戏：单人练习、约定房号联机、随机匹配。前端部署在 Cloudflare Pages，后端（房间状态 + 判定器）部署在 Cloudflare Worker，语义判定由 TypeSafe **Jev** 完成。

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
│           ├── judge.ts     Jev 判定器（score→关联度，noul→猜中）+ KV 缓存
│           ├── puzzles.ts   题库加载
│           └── data/word_data/  题库 JSON（14 个分类）
├── packages/shared/         前后端共享：规则常量、猜测词清洗、协议类型
├── ARCHITECTURE.md
└── API.md
```

## 本地开发

```bash
cd website
pnpm install
cp apps/worker/.dev.vars.example apps/worker/.dev.vars   # 默认 JEV_PROVIDER=mock，不联网
pnpm dev:worker    # wrangler dev，:8787
pnpm dev:web       # vite，:5173，/api 与 /ws 代理到 :8787
```

`pnpm typecheck` 对三个包做类型检查。

## 部署

```bash
cd website
pnpm deploy:worker   # wrangler deploy（apps/worker/wrangler.jsonc）
pnpm deploy:web      # vite build + wrangler pages deploy（apps/web/wrangler.toml）
```

- 先部署 Worker，再部署 Pages（Pages 的 Service Binding 依赖 Worker 已存在）。
- Worker 设置了 `workers_dev: false`，不暴露 `*.workers.dev`；浏览器只访问 Pages 域名。
- 自定义域名在控制台绑定：Pages → `wtf.plutokeating.beer`；Worker → `wtf.williamhvollita.dpdns.org`（可选，仅用于运维排障，不在前端出现）。

### Jev 判定通道

`apps/worker/wrangler.jsonc` 的 `JEV_PROVIDER` 选择主通道，另一通道可用时自动作为备用：

| 值 | 通道 | 前提 |
|---|---|---|
| `typesafe` | TypeSafe 直连 `api.typesafe.ai/v1/systemone` | `wrangler secret put TYPESAFE_API_KEY` |
| `workers-ai` | Workers AI binding `typesafe/jev` | 账户已充值 AI Gateway credits（不走每日免费 neurons） |
| `mock` | 本地伪分数 | 仅限本地开发 |

修改 `judge.ts` 中的评分量表后必须递增 `RUBRIC_VERSION`，使 KV 旧缓存失效。
