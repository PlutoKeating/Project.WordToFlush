"""
Danmaku manager: coordinates douyin and bilibili collectors,
forwards danmaku to SSE listeners and auto-guess bridge.

Maintains a dedicated asyncio event loop in a background thread
for running collector coroutines from Flask's threaded context.
"""

import asyncio
import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable

from admin.danmaku.douyin import DouyinCollector
from admin.danmaku.bilibili import BilibiliCollector

logger = logging.getLogger(__name__)


@dataclass
class CollectorState:
    platform: str
    room: str
    running: bool = False
    connected: bool = False
    error: str = ""
    collector: Optional[object] = None
    task: Optional[asyncio.Task] = None


class DanmakuManager:
    def __init__(self):
        self._collectors: list[CollectorState] = []
        self._sse_listeners: list[queue.Queue] = []
        self._auto_guess_callback: Optional[Callable] = None

        # Dedicated event loop for async operations
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._start_loop()

    def _start_loop(self):
        """Start a background asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_loop, daemon=True, name="danmaku-loop"
        )
        self._loop_thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro):
        """Schedule a coroutine on the background loop and wait for result."""
        if self._loop is None or self._loop.is_closed():
            raise RuntimeError("Event loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    def set_auto_guess_callback(self, callback: Callable):
        self._auto_guess_callback = callback

    def get_status(self) -> list[dict]:
        return [
            {
                "platform": c.platform,
                "room": c.room,
                "running": c.running,
                "connected": c.collector.connected if c.collector else False,
                "error": c.error,
            }
            for c in self._collectors
        ]

    def start_collector(
        self,
        platform: str,
        room: str,
    ):
        """Synchronous entry point for starting collector (called from Flask)."""
        self._run_async(self._start_collector_async(platform, room))

    def stop_collector(self, platform: str, room: str):
        """Synchronous entry point for stopping collector (called from Flask)."""
        self._run_async(self._stop_collector_async(platform, room))

    async def _start_collector_async(
        self,
        platform: str,
        room: str,
    ):
        # Stop existing collector for this platform+room
        await self._stop_collector_async(platform, room)

        state = CollectorState(platform=platform, room=room, running=True)
        self._collectors.append(state)

        def _on_danmaku(d: dict):
            self._publish_danmaku(d)

        try:
            if platform == "douyin":
                collector = DouyinCollector(room, _on_danmaku)
            elif platform == "bilibili":
                collector = BilibiliCollector(room, _on_danmaku)
            else:
                state.error = f"Unsupported platform: {platform}"
                state.running = False
                return

            state.collector = collector
            task = asyncio.create_task(collector.start())
            state.task = task
        except Exception as e:
            state.error = str(e)
            state.running = False
            state.connected = False
            raise

    async def _stop_collector_async(self, platform: str, room: str):
        for c in self._collectors:
            if c.platform == platform and c.room == room:
                if c.task and not c.task.done():
                    c.task.cancel()
                    try:
                        await c.task
                    except asyncio.CancelledError:
                        pass
                if c.collector:
                    try:
                        await c.collector.stop()
                    except Exception:
                        pass
                self._collectors.remove(c)
                break

    def _publish_danmaku(self, danmaku: dict):
        """Thread-safe publish to SSE listeners and auto-guess."""
        msg = json.dumps(danmaku, ensure_ascii=False)
        # Push to all SSE listeners
        dead: list[queue.Queue] = []
        for q in self._sse_listeners:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            if q in self._sse_listeners:
                self._sse_listeners.remove(q)

        # Auto-guess: schedule in background
        if self._auto_guess_callback:
            try:
                self._auto_guess_callback(danmaku)
            except Exception as e:
                logger.warning("auto_guess_callback error: %s", e)
        else:
            logger.debug("auto_guess_callback not set, danmaku not forwarded to bridge")

    def register_sse(self, q: queue.Queue):
        self._sse_listeners.append(q)

    def unregister_sse(self, q: queue.Queue):
        if q in self._sse_listeners:
            self._sse_listeners.remove(q)

    def shutdown(self):
        """Graceful shutdown."""
        import asyncio as _asyncio
        for c in list(self._collectors):
            try:
                self._run_async(self._stop_collector_async(c.platform, c.room))
            except Exception:
                pass
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
