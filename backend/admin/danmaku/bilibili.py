"""
Bilibili (B站) live danmaku collector.

Uses bilibili's official open API to fetch live room information
and connect to the live room WebSocket for danmaku messages.

Official API docs:
- https://open.bilibili.com/doc/4/da2b13dc-7f7a-0025-be11-0b677e793baa
- https://open.bilibili.com/doc/4/5cac94fe-57f9-06db-7515-523d81c44f85
"""

import asyncio
import hashlib
import json
import logging
import random
import struct
import time
from functools import reduce
from typing import Optional

import httpx
import websockets
from websockets.asyncio.client import connect as ws_connect

logger = logging.getLogger(__name__)

BILIBILI_API_LIVE_INFO = (
    "https://api.live.bilibili.com/room/v1/Room/room_init"
)
BILIBILI_API_DANMU_INFO = (
    "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo"
)
BILIBILI_API_NAV = (
    "https://api.bilibili.com/x/web-interface/nav"
)

_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 52, 44, 34,
]


def _get_mixin_key(orig: str) -> str:
    return reduce(lambda s, i: s + orig[i], _MIXIN_KEY_ENC_TAB, "")[:32]


def _sign_wbi_params(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = _get_mixin_key(img_key + sub_key)
    params["wts"] = int(time.time())
    params = dict(sorted(params.items()))
    query = "&".join(f"{k}={v}" for k, v in params.items())
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = w_rid
    return params

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)


def _clean_content(text: str) -> str:
    """Return non-empty content if it contains any text, empty string if purely non-text."""
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped


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
        self._wbi_img_key: str = ""
        self._wbi_sub_key: str = ""
        self.connected = False

    async def start(self):
        self._running = True
        reconnect_delay = 1
        await self._fetch_wbi_keys()
        while self._running:
            try:
                await self._connect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Bilibili collector error for room %s: %s", self.room_id, e)
            if self._running:
                logger.info(
                    "Bilibili: reconnecting to room %s in %ds...", self.room_id, reconnect_delay
                )
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        await self._client.aclose()

    async def _fetch_wbi_keys(self):
        try:
            resp = await self._client.get(BILIBILI_API_NAV)
            resp.raise_for_status()
            data = resp.json()
            wbi_img = data.get("data", {}).get("wbi_img", {})
            img_url = wbi_img.get("img_url", "")
            sub_url = wbi_img.get("sub_url", "")
            if img_url and sub_url:
                self._wbi_img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
                self._wbi_sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
                logger.debug("Bilibili: fetched Wbi keys for room %s", self.room_id)
            else:
                logger.warning("Bilibili: Wbi keys not found in nav response")
        except Exception as e:
            logger.warning("Bilibili: failed to fetch Wbi keys: %s", e)

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
                origin="https://live.bilibili.com",
                additional_headers={
                    "User-Agent": USER_AGENT,
                },
                ping_interval=None,
                close_timeout=5,
            ) as ws:
                self._ws = ws
                self.connected = True
                # Send auth packet
                await self._send_auth(ws)
                # Receive welcome + initial join message
                await self._ws_loop(ws)
        except Exception as e:
            logger.error("Bilibili WSS error for room %s: %s", self.room_id, e)
        finally:
            self.connected = False
            self._ws = None

    async def _get_danmu_info(self) -> Optional[dict]:
        try:
            params: dict = {"id": self.room_id, "type": "0"}
            if self._wbi_img_key and self._wbi_sub_key:
                params = _sign_wbi_params(params, self._wbi_img_key, self._wbi_sub_key)
            resp = await self._client.get(
                BILIBILI_API_DANMU_INFO,
                params=params,
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
        """Parse one or more Bilibili protocol packets from a single WebSocket frame."""
        offset = 0
        while offset + 16 <= len(data):
            try:
                total_len, header_len, proto_ver, op, seq = struct.unpack(
                    ">IHHII", data[offset:offset + 16]
                )
            except struct.error:
                break

            if header_len < 16 or total_len < header_len:
                break
            if offset + total_len > len(data):
                break

            body_start = offset + header_len
            body_end = offset + total_len
            body = data[body_start:body_end]

            if op == 3:
                try:
                    j = json.loads(body.decode("utf-8"))
                    online_count = j.get("count", 0)
                    logger.debug("Bilibili room %s OP3 online: %s", self.room_id, online_count)
                except Exception:
                    pass

            elif op == 5:
                self._handle_op5_body(body, proto_ver)

            elif op == 8:
                logger.info("Bilibili room %s auth success", self.room_id)

            else:
                logger.debug("Bilibili room %s op=%d seq=%d total=%d", self.room_id, op, seq, total_len)

            offset += total_len

    def _handle_op5_body(self, data: bytes, proto_ver: int):
        """Parse OP 5 body. proto_ver 0: raw JSON, 1: [4B len][JSON]..., 2/3: compressed then [4B len][JSON]..."""
        if proto_ver in (2, 3) and data:
            try:
                import brotli
                for attempt in ("brotli", "brotli_prefix4", "zlib"):
                    try:
                        if attempt == "brotli":
                            data = brotli.decompress(data)
                        elif attempt == "brotli_prefix4":
                            data = brotli.decompress(data[4:])
                        elif attempt == "zlib":
                            import zlib
                            data = zlib.decompress(data)
                        # After decompression, the data may be a nested Bilibili packet
                        # with its own header. Recursively handle it.
                        if len(data) >= 16:
                            self._handle_packet(data)
                            return
                        break
                    except Exception:
                        continue
                else:
                    logger.warning("Bilibili: cannot decompress proto_ver %d body (%d bytes)", proto_ver, len(data))
                    return
            except ImportError:
                logger.warning("Bilibili: brotli not installed for proto_ver %d", proto_ver)
                return

        if proto_ver == 0:
            try:
                j = json.loads(data.decode("utf-8", errors="replace"))
            except Exception:
                return
            self._process_single_json(j)
            return

        # proto_ver 1/2/3 after decompress: [4B len BE][JSON][4B len BE][JSON]...
        offset = 0
        sub_count = 0
        first_error = None
        while offset + 4 <= len(data):
            try:
                sub_len = struct.unpack(">I", data[offset:offset + 4])[0]
            except struct.error:
                break
            offset += 4
            if sub_len <= 0 or offset + sub_len > len(data):
                if first_error is None:
                    first_error = f"bad sub_len={sub_len} at offset={offset-4} total={len(data)}"
                break
            body_chunk = data[offset:offset + sub_len]
            offset += sub_len
            try:
                j = json.loads(body_chunk.decode("utf-8", errors="replace"))
            except Exception as e:
                if first_error is None:
                    first_error = f"json err at offset={offset-sub_len}: {e}"
                continue
            sub_count += 1
            self._process_single_json(j)
        if sub_count == 0 and first_error:
            logger.debug("Bilibili room %s OP5 parse failed: %s", self.room_id, first_error)
        elif sub_count > 0:
            logger.debug("Bilibili room %s OP5 parsed %d sub-packets", self.room_id, sub_count)

    def _process_single_json(self, j: dict):
        cmd = j.get("cmd", "")
        if cmd == "DANMU_MSG":
            logger.info("Bilibili room %s OP5 cmd: DANMU_MSG (processing...)", self.room_id)
        else:
            # Log non-repeating cmds at INFO, common ones at DEBUG
            if not hasattr(self, '_seen_cmds'):
                self._seen_cmds = set()
            if cmd not in self._seen_cmds:
                self._seen_cmds.add(cmd)
                logger.info("Bilibili room %s OP5 cmd: %s", self.room_id, cmd)

        if cmd != "DANMU_MSG":
            return

        info_list = j.get("info", [])
        if len(info_list) < 2:
            return

        content = str(info_list[1])
        user_arr = info_list[2] if len(info_list) > 2 else []
        user_name = str(user_arr[1]) if len(user_arr) > 1 else "匿名"

        clean_content = _clean_content(content)
        if not clean_content:
            return

        logger.info("Bilibili DANMU room %s: %s -> %s", self.room_id, user_name, clean_content)

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
                logger.exception("Bilibili on_danmaku callback failed")
