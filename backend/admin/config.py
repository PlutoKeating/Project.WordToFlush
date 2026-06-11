import os
from pathlib import Path
from dotenv import load_dotenv

_env_file = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_file)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_USERNAME and ADMIN_PASSWORD must be set in backend/.env"
    )

ADMIN_HOST_BIND_PORT = int(os.getenv("ADMIN_HOST_BIND_PORT", "8001"))
ADMIN_PORT = 8001

FLASK_SECRET_KEY = os.getenv(
    "FLASK_SECRET_KEY",
    os.urandom(24).hex(),
)

BACKEND_WS_URL = os.getenv(
    "BACKEND_WS_URL",
    "ws://localhost:8000/ws",
)
