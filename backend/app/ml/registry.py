"""Provider selection driven by configuration."""
from functools import lru_cache

from app.core.config import get_settings
from app.ml.base import EmbeddingProvider
from app.ml.stub import StubEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    name = get_settings().embedding_provider.lower()
    if name == "stub":
        return StubEmbeddingProvider()
    # Real providers (for example "bge_m3") are registered here on the
    # workstation once their weights are available. Falls back to the stub so
    # the service always starts.
    return StubEmbeddingProvider()


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return max(-1.0, min(1.0, dot))
