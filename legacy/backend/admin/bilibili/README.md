# bilibili 直播间弹幕获取方式

bilibili 直播间官方提供了直接获取直播间信息与全部实时弹幕内容的 API。实现参考了 B站官方开放平台文档及社区验证的 blivedm 库 (xfgryujk/blivedm)。

## 官方相关文档页面的链接

### 1. 直播房间长链信息及心跳ID
https://open.bilibili.com/doc/4/da2b13dc-7f7a-0025-be11-0b677e793baa

### 2. 长连说明
https://open.bilibili.com/doc/4/5cac94fe-57f9-06db-7515-523d81c44f85

### 3. 直播房间长链心跳
https://open.bilibili.com/doc/4/8f57c906-15e6-4e61-e850-da0911be1cf1

### 4. 直播间数据
https://open.bilibili.com/doc/4/c7b549c9-d5d6-0331-b510-465ed4107e01

## 社区验证文档（参考）

- B站直播 WebSocket 消息协议: https://github.com/lovelyyoshino/Bilibili-Live-API/blob/master/API.live_websocket.md
- 弹幕 Token 获取: https://github.com/lovelyyoshino/Bilibili-Live-API/blob/master/API.getDanmuInfo.md
- 房间初始化: https://github.com/lovelyyoshino/Bilibili-Live-API/blob/master/API.room_init.md
- 参考实现 (blivedm): https://github.com/xfgryujk/blivedm

## 当前实现流程

本项目的 BilibiliCollector (`backend/admin/danmaku/bilibili.py`) 采集链路:

```
启动采集
  ├─ _fetch_wbi_keys()    → /x/web-interface/nav     获取 Wbi 签名密钥
  ├─ _init_room_id()      → /room/v1/Room/get_info    短房间号→真实ID 解析
  ├─ _init_buvid()        → www.bilibili.com          获取 buvid3 反爬 Cookie
  └─ [循环重连]
       └─ _connect()
            ├─ _get_danmu_info()  → getDanmuInfo   获取 WSS 地址 + token
            └─ WSS 连接
                 ├─ _send_auth()     protover=3 + buvid + key(条件)
                 ├─ _heartbeat_loop()  30s 间隔, {} body
                 └─ _ws_loop()
                      ├─ _handle_packet()    16B 包头解析, 畸形数据逐字节跳过
                      │    └─ _handle_op5_body()
                      │         ├─ proto_ver=0 → raw JSON → _process_single_json()
                      │         ├─ proto_ver=1 → [4B len][JSON]... 解析
                      │         ├─ proto_ver=2 → zlib 解压 → 递归 _handle_packet()
                      │         └─ proto_ver=3 → brotli 解压 → 递归 _handle_packet()
                      └─ _process_single_json()
                           └─ cmd=="DANMU_MSG" → on_danmaku 回调
```

## 关键实现细节

| 要点 | 说明 |
|------|------|
| 房间号解析 | 支持短房间号 (如 `6`), 调用 `get_info` 转为真实 ID |
| 反爬措施 | 访问 bilibili.com 获取 `buvid3` Cookie, auth 包携带 `buvid` 字段 |
| 协议版本 | auth 声明 `protover=3` (brotli 压缩), 心跳 body 为 `{}` |
| 解压方式 | 按包头 `ver` 字段决定: 2→zlib, 3→brotli (含 4B 前缀 fallback) |
| 容错解析 | `_handle_packet` 和 proto_ver=1 路径遇到畸形数据时逐字节跳过, 不丢弃后续合法包 |
| 重连策略 | 断开后指数退避 (1s→2s→4s→...→60s), 成功重连后重置为 1s |
| 弹幕转发 | 自动猜词桥不设冷却, 每条弹幕即时全量转发到后端 |
