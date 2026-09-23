# API

所有路径相对前端同源（生产 `https://wtf.plutokeating.beer`），类型定义见 `packages/shared/src/protocol.ts`。

身份参数：`uid`（`[A-Za-z0-9_-]{8,64}`，前端首次访问生成并保存）、`name`（≤ 12 字，空则为 `玩家xxxx`）。

浏览器请求的 `Origin` 必须在 Worker 变量 `ALLOWED_ORIGINS` 中，否则 403。

## REST

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | `{ status: "ok" }` |
| POST | `/api/rooms` | body `{ mode: "solo" \| "private" }` → `{ code }` |
| GET | `/api/rooms/:code` | `{ code, mode, phase, players }`；不存在 404 |

## WebSocket

### `/ws/room/:code?uid&name`

消息格式 `{ event, data }`。

客户端 → 服务端：

| event | data | 权限 |
|---|---|---|
| `game:start` | – | lobby 阶段，房主 / solo |
| `game:guess` | `{ guess }` | playing 阶段；需与谜底同字数、纯汉字、间隔 ≥ 1.5 s、本题未猜过 |
| `game:skip` | – | playing 阶段，房主 / solo；直接揭晓，无人得分（安慰分照发） |
| `game:restart` | – | finished 阶段，房主 / solo |
| `ping` | – | 心跳，回 `pong` |

服务端 → 客户端：

| event | data |
|---|---|
| `room:state` | `RoomView`，任何状态变化后全量广播 |
| `game:guessResult` | `GuessView`，新猜测 |
| `error` | `{ message }`，仅发给出错的连接 |

连接被拒（房间不存在 / 已满 / 匹配房已开局）时握手直接失败；同一 uid 重复连接时旧连接以 close code `4000` 关闭。

### `/ws/match?uid&name`

| event | data |
|---|---|
| `match:waiting` | `{ count, startsAt }`，`startsAt` 为预计开局时间（人数不足 2 时为 null） |
| `match:found` | `{ code }`，随后服务端关闭连接，客户端连接 `/ws/room/:code` |

规则：满 4 人立即成局；首位排队者等待 30 秒后若 ≥ 2 人则成局。
