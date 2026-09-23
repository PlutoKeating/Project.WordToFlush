import math
import httpx
from app.config import OLLAMA_HOST, OLLAMA_MODEL

EMBEDDING_CACHE_MAX = 500


class VectorCalculator:
    def __init__(self):
        self.host = OLLAMA_HOST
        self.model = OLLAMA_MODEL
        self._embedding_cache: dict[str, list[float]] = {}
        self._affinity_cache: dict[str, float] = {}

    def _cache_key(self, guess: str, target: str) -> str:
        return f"{guess}::{target}"

    async def get_embedding(self, text: str) -> list[float]:
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.host}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()
            embedding: list[float] = response.json()["embedding"]

        if len(self._embedding_cache) >= EMBEDDING_CACHE_MAX:
            oldest = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest]

        self._embedding_cache[text] = embedding
        return embedding

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    async def calculate_affinity(self, guess: str, target: str) -> float:
        if guess == target:
            return 1.0

        key = self._cache_key(guess, target)
        if key in self._affinity_cache:
            return self._affinity_cache[key]

        vec_a = await self.get_embedding(guess)
        vec_b = await self.get_embedding(target)
        sim = self.cosine_similarity(vec_a, vec_b)
        result = max(0.0, min(1.0, sim))

        if len(self._affinity_cache) >= EMBEDDING_CACHE_MAX:
            oldest = next(iter(self._affinity_cache))
            del self._affinity_cache[oldest]
        self._affinity_cache[key] = result

        return result
