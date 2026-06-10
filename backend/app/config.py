from dotenv import load_dotenv
import os

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "all-minilm")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
