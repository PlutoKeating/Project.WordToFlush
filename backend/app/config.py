import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "bge-large-zh")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
