#!/usr/bin/env python3
"""
Run both FastAPI (main backend) and Flask (admin panel) together.

Called from the Docker CMD. Uses multiprocessing to run both servers
in the same container, and threads for the auto-guess bridge.
"""

import multiprocessing
import logging
import asyncio
import threading
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

logger = logging.getLogger("run_admin")


def _run_flask_with_bridge():
    """Run Flask admin + auto-guess bridge in the same process."""
    import admin.app as admin_app
    from admin.config import ADMIN_PORT, BACKEND_WS_URL

    # Create readiness event so Flask waits for bridge callback registration
    admin_app._auto_guess_ready = threading.Event()

    # Start auto-guess bridge in a background daemon thread
    def _bridge_main():
        asyncio.run(admin_app.start_auto_guess_bridge(BACKEND_WS_URL))

    bridge_thread = threading.Thread(target=_bridge_main, daemon=True, name="auto-guess-bridge")
    bridge_thread.start()
    logger.info("Auto-guess bridge thread started")

    # Wait for bridge to register callback (timeout 10s)
    if not admin_app._auto_guess_ready.wait(timeout=10):
        logger.warning("Auto-guess bridge callback not registered within 10s, starting Flask anyway")

    # Start Flask
    app = admin_app.app
    try:
        from waitress import serve
        logger.info("Starting Flask (waitress) on port %d", ADMIN_PORT)
        serve(app, host="0.0.0.0", port=ADMIN_PORT, threads=4, send_bytes=1)
    except ImportError:
        logger.info("Starting Flask (dev server) on port %d", ADMIN_PORT)
        app.run(host="0.0.0.0", port=ADMIN_PORT, debug=False, threaded=True)


def _run_fastapi():
    """Run FastAPI main backend on port 8000."""
    import uvicorn
    logger.info("Starting FastAPI on port 8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")


def main():
    logger.info("Starting WordToFlush services...")

    # Start Flask + Auto-guess bridge in a child process
    p_flask = multiprocessing.Process(
        target=_run_flask_with_bridge, name="flask-admin", daemon=True
    )
    p_flask.start()

    # Start FastAPI in the main process (foreground)
    _run_fastapi()


if __name__ == "__main__":
    main()
