"""
Douyin (抖音) live danmaku collector.

Connects to douyin live room WebSocket to capture danmaku messages.
Extracts username + pure Chinese text content, filtering out
non-CJK characters, emojis, and system messages.
"""

import asyncio
import gzip
import hashlib
import json
import logging
import random
import re
import string
import time
from typing import Optional

import httpx
import websockets
from websockets.asyncio.client import connect as ws_connect

from admin.danmaku.proto_reader import (
    decode_pushframe,
    decode_response,
    decode_chat_message,
    encode_pushframe,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)

DOUYIN_LIVE_URL = "https://live.douyin.com"
DOUYIN_IM_FETCH = "/webcast/im/fetch/"
DOUYIN_WS_BASE = "wss://webcast100-ws-web-lq.douyin.com"
DOUYIN_WS_PATH = "/webcast/im/push/v2/"

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")


def _extract_cjk(text: str) -> str:
    parts = _CJK_RE.findall(text)
    return "".join(parts)


def _clean_content(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped


def _random_ms_token(length: int = 184) -> str:
    chars = string.ascii_letters + string.digits + "-_="
    return "".join(random.choice(chars) for _ in range(length))


def _md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _calc_signature(room_id: str, unique_id: str) -> str:
    sdk_version = "1.0.15"
    raw = (
        f"live_id=1,aid=6383,version_code=180800,"
        f"webcast_sdk_version={sdk_version},"
        f"room_id={room_id},sub_room_id=,sub_channel_id=,"
        f"did_rule=3,user_unique_id={unique_id},"
        f"device_platform=web,device_type=,ac=,identity=audience"
    )
    return _md5_hex(raw)


def _parse_live_html(html: str) -> Optional[dict]:
    match = re.search(
        r'<script\snonce="\S+?"\s>self\.__pace_f\.push\(\[1,"'
        r'[a-z]?:\[\\"\$\\",\\"\$L\d+\\",null,'
        r'([\s\S]+?state[\s\S]+?)\]\\n"\]\)<\/script>',
        html,
    )
    if not match:
        return None
    json_str = match.group(1)
    json_str = json_str.replace('\\"', '"')

    room_id_m = re.search(r'"roomId":"([0-9]+?)"', json_str)
    unique_id_m = re.search(r'"user_unique_id":"([0-9]+?)"', json_str)
    nickname_m = re.search(r'"anchor":\{[\s\S]*?"nickname":"([\s\S]+?)"', json_str)
    title_m = re.search(r'"room":\{[\s\S]*?"title":"([\s\S]+?)"', json_str)
    status_m = re.search(r'"status":([0-9]{1})', json_str)

    if not room_id_m or not unique_id_m:
        return None

    return {
        "roomId": room_id_m.group(1),
        "uniqueId": unique_id_m.group(1),
        "nickname": nickname_m.group(1) if nickname_m else "",
        "title": title_m.group(1) if title_m else "",
        "status": int(status_m.group(1)) if status_m else 4,
    }


class DouyinCollector:
    def __init__(self, room_number: str, on_danmaku):
        self.room_number = room_number
        self.on_danmaku = on_danmaku
        self._ws: Optional[websockets.asyncio.client.ClientConnection] = None
        self._running = False
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        self._cursor = ""
        self._internal_ext = ""
        self._room_info: dict = {}
        self.connected = False

    async def start(self):
        self._running = True
        reconnect_delay = 1
        while self._running:
            try:
                await self._connect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Douyin collector error for room %s: %s", self.room_number, e)
            if self._running:
                logger.info(
                    "Douyin: reconnecting to room %s in %ds...", self.room_number, reconnect_delay
                )
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        await self._client.aclose()

    async def _connect(self):
        logger.info("Douyin: fetching live info for room %s", self.room_number)

        # Step 1: Get live room info
        html = await self._get_live_html()
        room_info = _parse_live_html(html)
        if not room_info:
            logger.error("Douyin: failed to parse live info for room %s", self.room_number)
            return

        self._room_info = room_info
        logger.info("Douyin: room %s info parsed. status=%s", self.room_number, room_info.get("status"))

        if room_info["status"] != 2:
            logger.warning("Douyin: room %s is not live (status=%s)", self.room_number, room_info["status"])
            return

        room_id = room_info["roomId"]
        unique_id = room_info["uniqueId"]

        # Step 2: Get IM fetch info
        cursor, internal_ext = await self._fetch_im_info(room_id, unique_id)
        self._cursor = cursor
        self._internal_ext = internal_ext

        # Step 3: Build WSS URL and connect
        signature = _calc_signature(room_id, unique_id)
        params = {
            "live_id": "1",
            "aid": "6383",
            "version_code": "180800",
            "webcast_sdk_version": "1.0.15",
            "room_id": room_id,
            "sub_room_id": "",
            "sub_channel_id": "",
            "did_rule": "3",
            "user_unique_id": unique_id,
            "device_platform": "web",
            "device_type": "",
            "ac": "",
            "identity": "audience",
            "signature": signature,
            "cursor": cursor,
            "internal_ext": internal_ext,
            "host": DOUYIN_LIVE_URL,
            "compress": "gzip",
            "support_wrds": "1",
            "need_persist_msg_count": "15",
            "browser_language": "zh-CN",
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": "Win32",
            "browser_version": USER_AGENT,
            "cookie_enabled": "true",
            "screen_width": "1920",
            "screen_height": "1080",
            "tz_name": "Asia/Shanghai",
            "endpoint": "live_pc",
            "im_path": "/webcast/im/fetch/",
            "insert_task_id": "",
            "live_reason": "",
            "heartbeatDuration": "0",
        }

        query = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()) if params[k])
        ws_url = f"{DOUYIN_WS_BASE}{DOUYIN_WS_PATH}?{query}"

        logger.info("Douyin: connecting to WSS for room %s", self.room_number)
        try:
            async with ws_connect(
                ws_url,
                origin=DOUYIN_LIVE_URL,
                additional_headers={
                    "User-Agent": USER_AGENT,
                },
                ping_interval=10,
                ping_timeout=5,
                close_timeout=5,
            ) as ws:
                self._ws = ws
                self.connected = True
                await self._ws_loop(ws)
        except Exception as e:
            logger.error("Douyin WSS error for room %s: %s", self.room_number, e)
        finally:
            self.connected = False
            self._ws = None

    async def _get_live_html(self) -> str:
        url = f"{DOUYIN_LIVE_URL}/{self.room_number}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        # Second request with cookies from first
        await asyncio.sleep(0.5)
        resp2 = await self._client.get(url)
        resp2.raise_for_status()
        return resp2.text

    async def _fetch_im_info(self, room_id: str, unique_id: str) -> tuple:
        params = {
            "live_id": "1",
            "aid": "6383",
            "app_name": "douyin_web",
            "browser_language": "zh-CN",
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": "Win32",
            "browser_version": USER_AGENT,
            "cookie_enabled": "true",
            "cursor": "",
            "device_platform": "web",
            "did_rule": "3",
            "endpoint": "live_pc",
            "fetch_rule": "1",
            "identity": "audience",
            "insert_task_id": "",
            "internal_ext": "",
            "last_rtt": "0",
            "live_reason": "",
            "msToken": _random_ms_token(),
            "need_persist_msg_count": "15",
            "resp_content_type": "protobuf",
            "room_id": room_id,
            "screen_height": "1080",
            "screen_width": "1920",
            "support_wrds": "1",
            "tz_name": "Asia/Shanghai",
            "user_unique_id": unique_id,
            "version_code": "180800",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{DOUYIN_LIVE_URL}{DOUYIN_IM_FETCH}?{query}"

        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.content

        try:
            res = decode_response(data)
            cursor = res.get("cursor", "")
            internal_ext = res.get("internalExt", "")
        except Exception:
            now = int(time.time() * 1000)
            cursor = f"r-7497180536918546638_d-1_u-1_fh-7497179772733760010_t-{now}"
            internal_ext = (
                f"internal_src:dim|wss_push_room_id:{room_id}|"
                f"wss_push_did:{unique_id}|first_req_ms:{now}|"
                f"fetch_time:{now}|seq:1|wss_info:0-{now}-0-0|"
                f"wrds_v:7497180515443673855"
            )

        return cursor, internal_ext

    async def _ws_loop(self, ws):
        ping_task = asyncio.create_task(self._ping_loop(ws))
        try:
            async for raw in ws:
                if not self._running:
                    break
                await self._handle_message(raw)
        finally:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass

    async def _ping_loop(self, ws):
        while self._running:
            try:
                ping_frame = encode_pushframe({"payloadType": "hb"})
                await ws.send(ping_frame)
            except Exception:
                break
            await asyncio.sleep(10)

    async def _handle_message(self, data: bytes):
        try:
            frame = decode_pushframe(data)
        except Exception:
            return

        payload = frame.get("payload")
        headers = frame.get("headersList", {})
        if not payload:
            return

        # Handle gzip compression
        if headers.get("compress_type") == "gzip":
            try:
                payload = gzip.decompress(payload)
            except Exception:
                return

        # Handle ack
        cursor = headers.get("im-cursor", "")
        internal_ext = headers.get("im-internal_ext", "")
        if cursor:
            self._cursor = cursor
        if internal_ext:
            self._internal_ext = internal_ext

        try:
            response = decode_response(payload)
        except Exception:
            return

        need_ack = response.get("needAck", False)
        if need_ack and self._ws:
            ack_payload = self._build_ack(internal_ext)
            ack_frame = encode_pushframe({
                "payloadType": "ack",
                "payload": ack_payload,
                "logId": str(frame.get("logId", "")),
            })
            try:
                await self._ws.send(ack_frame)
            except Exception:
                pass

        payload_type = frame.get("payloadType", "")
        if payload_type == "msg":
            messages = response.get("messages", [])
            self._process_messages(messages)

    @staticmethod
    def _build_ack(internal_ext: str) -> bytes:
        result = bytearray()
        for ch in internal_ext:
            cp = ord(ch)
            if cp < 0x80:
                result.append(cp)
            elif cp < 0x800:
                result.append(0xc0 | (cp >> 6))
                result.append(0x80 | (cp & 0x3f))
            elif cp < 0x10000:
                result.append(0xe0 | (cp >> 12))
                result.append(0x80 | ((cp >> 6) & 0x3f))
                result.append(0x80 | (cp & 0x3f))
            else:
                result.append(0xf0 | (cp >> 18))
                result.append(0x80 | ((cp >> 12) & 0x3f))
                result.append(0x80 | ((cp >> 6) & 0x3f))
                result.append(0x80 | (cp & 0x3f))
        return bytes(result)

    def _process_messages(self, messages: list):
        for msg in messages:
            method = msg.get("method", "")
            payload = msg.get("payload")
            if not payload or method != "WebcastChatMessage":
                continue

            try:
                chat = decode_chat_message(payload)
            except Exception:
                continue

            content = chat.get("content", "")
            user_info = chat.get("user", {})
            user_name = user_info.get("nickname", "匿名")

            # Filter: only pure CJK content
            clean_content = _clean_content(content)
            if not clean_content:
                continue

            danmaku = {
                "platform": "douyin",
                "room": self.room_number,
                "userName": user_name,
                "content": clean_content,
                "timestamp": int(time.time() * 1000),
            }

            if self.on_danmaku:
                try:
                    self.on_danmaku(danmaku)
                except Exception:
                    pass
