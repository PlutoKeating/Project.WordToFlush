from pathlib import Path
from dotenv import load_dotenv
import os

_env_file = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_file)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "all-minilm")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

WIN_AFFINITY_THRESHOLD = float(
    os.getenv("WIN_AFFINITY_THRESHOLD", "0.92")
)
