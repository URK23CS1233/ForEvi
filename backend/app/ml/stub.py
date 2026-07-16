"""Deterministic stub embedding provider.

Produces a stable unit vector from a hashed bag of tokens, so that identical
text always maps to the same vector and similar text shares direction. This is
not a semantic model; it exists so the ingestion, storage, retrieval and
consistency pipeline is exercisable and testable before real encoders are
attached on the workstation.
"""
import hashlib
import math
import re

from app.ml.base import EMBED_DIM, EmbeddingProvider

_TOK = re.compile(r"[a-z0-9]+")


class StubEmbeddingProvider(EmbeddingProvider):
    name = "stub"
    dim = EMBED_DIM

    def embed_text(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _TOK.findall((text or "").lower()) or ["_empty_"]
        for tok in tokens:
            h = hashlib.sha256(tok.encode()).digest()
            idx = int.from_bytes(h[:4], "big") % self.dim
            sign = 1.0 if h[4] & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
