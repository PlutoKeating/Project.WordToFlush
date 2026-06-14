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

BILIBILI_API_GET_INFO = (
    "https://api.live.bilibili.com/room/v1/Room/get_info"
)
BILIBILI_API_DANMU_INFO = (
    "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo"
)
BILIBILI_API_NAV = (
    "https://api.bilibili.com/x/web-interface/nav"
)
BILIBILI_HOME = "https://www.bilibili.com/"

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
        room_id: bilibili live room ID (numeric string, supports short IDs)
        on_danmaku: callback receiving dict with keys:
            platform, room, userName, content, timestamp
        """
        self.room_id = room_id
        self.real_room_id = room_id  # resolved via get_info
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
        self._buvid: str = ""
        self.connected = False

    async def start(self):
        self._running = True
        reconnect_delay = 1
        await self._fetch_wbi_keys()
        await self._init_room_id()
        await self._init_buvid()
        while self._running:
            try:
                await self._connect()
                reconnect_delay = 1  # reset on successful connection cycle
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

    async def _init_room_id(self):
        """Resolve short room ID to real room ID via get_info API."""
        try:
            resp = await self._client.get(
                BILIBILI_API_GET_INFO,
                params={"room_id": self.room_id},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0 and data.get("data", {}).get("room_id"):
                real_id = str(data["data"]["room_id"])
                if real_id != self.room_id:
                    logger.info(
                        "Bilibili: resolved room %s → real room %s",
                        self.room_id, real_id,
                    )
                self.real_room_id = real_id
            else:
                logger.warning(
                    "Bilibili: get_info failed for room %s, code=%s msg=%s",
                    self.room_id, data.get("code"), data.get("message", ""),
                )
        except Exception as e:
            logger.warning("Bilibili: get_info request failed: %s, using raw room_id", e)

    async def _init_buvid(self):
        """Fetch a buvid3 cookie from Bilibili home page if not already set."""
        try:
            # Visit bilibili.com to get buvid3 cookie from Set-Cookie header
            resp = await self._client.get(BILIBILI_HOME)
            # httpx stores cookies from Set-Cookie in the client's cookie jar
            for cookie in self._client.cookies.jar:
                if cookie.name == "buvid3" and cookie.value:
                    self._buvid = cookie.value
                    logger.debug("Bilibili: got buvid3=%s...", self._buvid[:12])
                    return
            # Fallback: generate a synthetic buvid
            self._buvid = "".join(
                random.choices("0123456789ABCDEF", k=32)
            )
            logger.debug("Bilibili: generated synthetic buvid=%s...", self._buvid[:12])
        except Exception as e:
            logger.warning("Bilibili: failed to init buvid: %s", e)
            self._buvid = "".join(random.choices("0123456789ABCDEF", k=32))

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
            params: dict = {"id": self.real_room_id, "type": "0"}
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
        auth_body: dict = {
            "uid": 0,
            "roomid": int(self.real_room_id),
            "protover": 3,
            "platform": "web",
            "type": 2,
        }
        if self._token:
            auth_body["key"] = self._token
        if self._buvid:
            auth_body["buvid"] = self._buvid

        auth_packet = json.dumps(auth_body, ensure_ascii=False)

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
        """Send heartbeat every 30 seconds with {} body (Bilibili protocol standard)."""
        heartbeat_body = b"{}"
        while self._running:
            try:
                hb = struct.pack(">IHHII", 16 + len(heartbeat_body), 16, 1, 2, 1) + heartbeat_body
                await ws.send(hb)
            except Exception:
                break
            await asyncio.sleep(30)

    def _handle_packet(self, data: bytes):
        """Parse one or more Bilibili protocol packets from a single WebSocket frame.

        On malformed data, skips forward byte-by-byte to find the next valid header
        instead of abandoning all remaining data.
        """
        offset = 0
        skip_count = 0
        max_skips = len(data)  # safety bound
        while offset + 16 <= len(data):
            try:
                total_len, header_len, proto_ver, op, seq = struct.unpack(
                    ">IHHII", data[offset:offset + 16]
                )
            except struct.error:
                logger.debug("Bilibili room %s struct.unpack failed at offset=%d, skipping 1 byte", self.room_id, offset)
                offset += 1
                skip_count += 1
                if skip_count > max_skips:
                    break
                continue

            if header_len < 16 or total_len < header_len:
                logger.debug("Bilibili room %s bad header_len=%d total_len=%d at offset=%d", self.room_id, header_len, total_len, offset)
                offset += 1
                skip_count += 1
                if skip_count > max_skips:
                    break
                continue
            if offset + total_len > len(data):
                logger.debug("Bilibili room %s packet truncated: total_len=%d beyond buffer at offset=%d", self.room_id, total_len, offset)
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
            skip_count = 0  # reset on successful parse

    def _handle_op5_body(self, data: bytes, proto_ver: int):
        """Parse OP 5 body.

        proto_ver 0: raw JSON
        proto_ver 1: [4B len BE][JSON]... (uncompressed, rarely used)
        proto_ver 2: zlib-compressed, then nested Bilibili packets
        proto_ver 3: brotli-compressed, then nested Bilibili packets
        """
        if proto_ver in (2, 3) and data:
            original_len = len(data)
            try:
                if proto_ver == 2:
                    import zlib
                    data = zlib.decompress(data)
                    logger.debug("Bilibili room %s zlib: %d→%d bytes", self.room_id, original_len, len(data))
                elif proto_ver == 3:
                    import brotli
                    try:
                        data = brotli.decompress(data)
                    except Exception:
                        # Some servers prepend a 4-byte length prefix
                        data = brotli.decompress(data[4:])
                    logger.debug("Bilibili room %s brotli: %d→%d bytes", self.room_id, original_len, len(data))
            except ImportError as e:
                logger.warning("Bilibili: decompression library missing for proto_ver %d: %s", proto_ver, e)
                return
            except Exception as e:
                logger.warning("Bilibili: decompression failed for proto_ver %d (%d bytes): %s", proto_ver, original_len, e)
                return

            if len(data) >= 16:
                # Decompressed data contains nested Bilibili packets with 16-byte headers
                self._handle_packet(data)
            else:
                logger.warning("Bilibili room %s decompressed data too small (%d bytes)", self.room_id, len(data))
            return

        if proto_ver == 0:
            try:
                j = json.loads(data.decode("utf-8", errors="replace"))
            except Exception:
                return
            self._process_single_json(j)
            return

        # proto_ver 1: [4B len BE][JSON][4B len BE][JSON]...
        offset = 0
        sub_count = 0
        skip_count = 0
        max_skips = len(data)
        while offset + 4 <= len(data):
            try:
                sub_len = struct.unpack(">I", data[offset:offset + 4])[0]
            except struct.error:
                offset += 1
                skip_count += 1
                if skip_count > max_skips:
                    break
                continue
            offset += 4
            if sub_len <= 0 or offset + sub_len > len(data):
                logger.debug(
                    "Bilibili room %s bad sub_len=%d at offset=%d total=%d",
                    self.room_id, sub_len, offset - 4, len(data),
                )
                offset += 1
                skip_count += 1
                if skip_count > max_skips:
                    break
                continue
            body_chunk = data[offset:offset + sub_len]
            offset += sub_len
            try:
                j = json.loads(body_chunk.decode("utf-8", errors="replace"))
            except Exception:
                continue
            sub_count += 1
            self._process_single_json(j)
            skip_count = 0
        if sub_count == 0 and skip_count > 0:
            logger.debug("Bilibili room %s OP5 proto_ver=1 parse: no valid sub-packets found", self.room_id)
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
            "room": self.real_room_id,
            "userName": user_name,
            "content": clean_content,
            "timestamp": int(time.time() * 1000),
        }
        if self.on_danmaku:
            try:
                self.on_danmaku(danmaku)
            except Exception:
                logger.exception("Bilibili on_danmaku callback failed")
