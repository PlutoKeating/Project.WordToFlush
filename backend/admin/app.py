"""
Flask admin application.

Serves:
- Login page / login API
- Dashboard page
- SSE stream for real-time danmaku
- Collector control APIs
- Auto-guess bridge to main backend WebSocket
"""

import asyncio
import json
import logging
import queue

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    Response,
)
import websockets
from websockets.client import ClientConnection

from admin.config import FLASK_SECRET_KEY
from admin.auth import login_required, verify_credentials
from admin.danmaku import danmaku_manager

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder="templates",
)
app.secret_key = FLASK_SECRET_KEY

_auto_guess_state: dict = {
    "enabled": True,
}


def _create_app():
    return app


@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/login")
def login_page():
    if session.get("admin_authenticated"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if verify_credentials(username, password):
        session["admin_authenticated"] = True
        session.permanent = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "用户名或密码错误"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/status")
@login_required
def api_status():
    return jsonify({
        "collectors": danmaku_manager.get_status(),
        "autoGuess": _auto_guess_state,
    })


@app.route("/api/danmaku/start", methods=["POST"])
@login_required
def api_danmaku_start():
    data = request.get_json(silent=True) or {}
    platform = data.get("platform", "").strip().lower()
    room = data.get("room", "").strip()

    if not platform or platform not in ("douyin", "bilibili"):
        return jsonify({"ok": False, "error": "平台仅支持 douyin 或 bilibili"}), 400
    if not room:
        return jsonify({"ok": False, "error": "请输入房间号"}), 400

    try:
        danmaku_manager.start_collector(platform, room)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/danmaku/stop", methods=["POST"])
@login_required
def api_danmaku_stop():
    data = request.get_json(silent=True) or {}
    platform = data.get("platform", "").strip().lower()
    room = data.get("room", "").strip()

    if not platform or not room:
        return jsonify({"ok": False, "error": "缺少参数"}), 400

    try:
        danmaku_manager.stop_collector(platform, room)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auto-guess", methods=["POST"])
@login_required
def api_auto_guess_toggle():
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled", True)

    _auto_guess_state["enabled"] = enabled

    return jsonify({"ok": True, "state": _auto_guess_state})


@app.route("/api/danmaku/stream")
@login_required
def api_danmaku_stream():
    def generate():
        q: queue.Queue = queue.Queue(maxsize=256)
        danmaku_manager.register_sse(q)
        try:
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            danmaku_manager.unregister_sse(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


_auto_guess_ws: ClientConnection | None = None
_auto_guess_loop: asyncio.AbstractEventLoop | None = None
_auto_guess_user_ids: dict[str, str] = {}
_auto_guess_last_sent: dict[str, float] = {}
GLOBAL_ROOM = "global"
DANMAKU_MIN_INTERVAL = 1.0  # seconds per user


def _schedule_bridge_guess(danmaku: dict):
    """Called from _publish_danmaku (thread context). Forward danmaku to backend as guess.

    Rate-limited: at most one guess per user per second.
    """
    global _auto_guess_loop, _auto_guess_ws, _auto_guess_user_ids, _auto_guess_last_sent
    import time as _time

    if not _auto_guess_state["enabled"]:
        return
    if _auto_guess_loop is None or _auto_guess_loop.is_closed():
        return

    content = danmaku.get("content", "")
    user_name = danmaku.get("userName", "匿名")

    if not content:
        return

    platform = danmaku.get("platform", "unknown")
    room = danmaku.get("room", "0")
    uid_key = f"{platform}:{room}:{user_name}"

    now = _time.time()
    last = _auto_guess_last_sent.get(uid_key, 0)
    if now - last < DANMAKU_MIN_INTERVAL:
        return
    _auto_guess_last_sent[uid_key] = now

    if uid_key not in _auto_guess_user_ids:
        _auto_guess_user_ids[uid_key] = f"danmaku-{abs(hash(uid_key)) % 100000}"
    user_id = _auto_guess_user_ids[uid_key]

    async def _send_guess():
        global _auto_guess_ws
        if not _auto_guess_ws:
            return
        try:
            msg = json.dumps({
                "event": "game:guess",
                "data": {
                    "roomId": GLOBAL_ROOM,
                    "userId": user_id,
                    "userName": user_name,
                    "guess": content,
                },
            }, ensure_ascii=False)
            await _auto_guess_ws.send(msg)
        except Exception:
            pass

    try:
        asyncio.run_coroutine_threadsafe(_send_guess(), _auto_guess_loop)
    except Exception:
        pass


async def start_auto_guess_bridge(backend_ws_url: str):
    """Connect to main backend WebSocket for forwarding danmaku as guesses."""
    global _auto_guess_ws, _auto_guess_loop
    _auto_guess_loop = asyncio.get_running_loop()

    danmaku_manager.set_auto_guess_callback(_schedule_bridge_guess)

    while True:
        try:
            async with websockets.connect(backend_ws_url) as ws:
                _auto_guess_ws = ws
                logger.info("Auto-guess bridge connected to backend")

                join_msg = json.dumps({
                    "event": "room:join",
                    "data": {
                        "roomId": GLOBAL_ROOM,
                        "platform": "bilibili",
                    },
                }, ensure_ascii=False)
                await ws.send(join_msg)

                async for raw in ws:
                    pass

        except Exception as e:
            logger.warning("Auto-guess bridge disconnected: %s. Reconnecting in 5s...", e)
            _auto_guess_ws = None
            await asyncio.sleep(5)
