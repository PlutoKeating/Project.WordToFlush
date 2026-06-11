"""
Bilibili (B站) live danmaku collector.

Uses bilibili's official open API to fetch live room information
and connect to the live room WebSocket for danmaku messages.

Official API docs:
- https://open.bilibili.com/doc/4/da2b13dc-7f7a-0025-be11-0b677e793baa
- https://open.bilibili.com/doc/4/5cac94fe-57f9-06db-7515-523d81c44f85
"""

import asyncio
import json
import logging
import random
import re
import struct
import time
from typing import Optional

import httpx
import websockets
from websockets.asyncio.client import connect as ws_connect

logger = logging.getLogger(__name__)

BILIBILI_API_LIVE_INFO = (
    "https://api.live.bilibili.com/room/v1/Room/room_init"
)
BILIBILI_API_DANMAKU_INFO = (
    "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")


def _extract_cjk(text: str) -> str:
    parts = _CJK_RE.findall(text)
    return "".join(parts)


class BilibiliCollector:
    def __init__(self, room_id: str, on_danmaku):
        """
        room_id: bilibili live room ID (numeric string)
        on_danmaku: callback receiving dict with keys:
            platform, room, userName, content, timestamp
        """
        self.room_id = room_id
        self.on_danmaku = on_danmaku
        self._ws: Optional[websockets.asyncio.client.ClientConnection] = None
        self._running = False
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={
                "User-Agent": USER_AGENT,
                "Referer": "https://live.bilibili.com/",
            },
            follow_redirects=True,
        )
        self._token = ""

    async def start(self):
        self._running = True
        try:
            await self._connect()
        except Exception as e:
            logger.error("Bilibili collector failed for room %s: %s", self.room_id, e)

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        await self._client.aclose()

    async def _connect(self):
        logger.info("Bilibili: fetching danmaku info for room %s", self.room_id)

        # Get danmu info (WebSocket server + token)
        info = await self._get_danmu_info()
        if not info:
            logger.error("Bilibili: failed to get danmu info for room %s", self.room_id)
            return

        host_list = info.get("host_list", [])
        token = info.get("token", "")
        self._token = token

        if not host_list:
            logger.error("Bilibili: no WebSocket hosts for room %s", self.room_id)
            return

        # Pick a random host
        host = random.choice(host_list)
        ws_url = f"wss://{host['host']}:{host['wss_port']}/sub"

        logger.info("Bilibili: connecting to WSS %s", ws_url)

        try:
            async with ws_connect(
                ws_url,
                extra_headers={
                    "User-Agent": USER_AGENT,
                    "Origin": "https://live.bilibili.com",
                },
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
            ) as ws:
                self._ws = ws
                # Send auth packet
                await self._send_auth(ws)
                # Receive welcome + initial join message
                await self._ws_loop(ws)
        except Exception as e:
            logger.error("Bilibili WSS error for room %s: %s", self.room_id, e)

    async def _get_danmu_info(self) -> Optional[dict]:
        try:
            resp = await self._client.get(
                BILIBILI_API_DANMU_INFO,
                params={"id": self.room_id, "type": "0"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error(
                    "Bilibili danmu info API error: code=%s msg=%s",
                    data.get("code"),
                    data.get("message", ""),
                )
                return None
            return data.get("data", {})
        except Exception as e:
            logger.error("Bilibili danmu info request failed: %s", e)
            return None

    async def _send_auth(self, ws):
        """Send bilibili live WebSocket auth packet."""
        auth_packet = json.dumps({
            "uid": 0,
            "roomid": int(self.room_id),
            "protover": 1,
            "platform": "web",
            "type": 2,
            "key": self._token,
        }, ensure_ascii=False)

        # Bilibili WebSocket protocol: header + body
        # Header: 16 bytes total
        #   [0:4] total_len (uint32 big-endian)
        #   [4:6] header_len (uint16 big-endian) = 16
        #   [6:8] proto_ver (uint16 big-endian)
        #   [8:12] operation (uint32 big-endian) = 7 for auth
        #   [12:16] sequence (uint32 big-endian) = 1
        body = auth_packet.encode("utf-8")
        header = struct.pack(
            ">IHHII",
            16 + len(body),  # total length
            16,              # header length
            1,               # protocol version
            7,               # OP_AUTH
            1,               # sequence
        )
        await ws.send(header + body)

    async def _ws_loop(self, ws):
        """Main WebSocket receive loop."""
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))
        try:
            async for raw in ws:
                if not self._running:
                    break
                self._handle_packet(raw)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _heartbeat_loop(self, ws):
        """Send heartbeat every 30 seconds."""
        while self._running:
            try:
                # OP_HEARTBEAT = 2
                hb = struct.pack(">IHHII", 16, 16, 1, 2, 1)
                await ws.send(hb)
            except Exception:
                break
            await asyncio.sleep(30)

    def _handle_packet(self, data: bytes):
        if len(data) < 16:
            return

        try:
            total_len, header_len, proto_ver, op, seq = struct.unpack(
                ">IHHII", data[:16]
            )
        except struct.error:
            return

        body = data[header_len:total_len]

        if op == 3:
            # OP_HEARTBEAT_REPLY - online count
            try:
                j = json.loads(body.decode("utf-8"))
                online_count = j.get("count", 0)
                logger.debug("Bilibili room %s online: %s", self.room_id, online_count)
            except Exception:
                pass

        elif op == 5:
            # OP_SEND_SMS_REPLY - danmaku message
            self._handle_raw_packets(body)

        elif op == 8:
            # OP_AUTH_REPLY
            logger.info("Bilibili room %s auth success", self.room_id)

    def _handle_raw_packets(self, data: bytes):
        """Handle proto_ver 0/1/2 raw packets (no brotli compression)."""
        try:
            j = json.loads(data.decode("utf-8", errors="replace"))
        except Exception:
            return

        cmd = j.get("cmd", "")

        if cmd == "DANMU_MSG":
            info_list = j.get("info", [])
            if len(info_list) < 2:
                return

            content = str(info_list[1]) if len(info_list) > 1 else ""
            user_arr = info_list[2] if len(info_list) > 2 else []
            user_name = str(user_arr[1]) if len(user_arr) > 1 else "匿名"

            clean_content = _extract_cjk(content)
            if not clean_content:
                return

            danmaku = {
                "platform": "bilibili",
                "room": self.room_id,
                "userName": user_name,
                "content": clean_content,
                "timestamp": int(time.time() * 1000),
            }

            if self.on_danmaku:
                try:
                    self.on_danmaku(danmaku)
                except Exception:
                    pass
