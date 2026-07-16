"""Pluggable embedding provider interface.

The platform depends only on this interface. A deterministic stub is used by
default so the whole pipeline runs end to end without any model download. On an
operational workstation a real provider (for example a multilingual text model
and an image model exported to a local runtime) is selected through configuration,
with no change to the calling code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

EMBED_DIM = 512


class EmbeddingProvider(ABC):
    name: str = "base"
    dim: int = EMBED_DIM

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]
