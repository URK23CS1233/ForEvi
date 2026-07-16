"""Trained tamper and consistency scorer used at inference time.

Loads the model produced by training/train_consistency.py and scores each
artifact of a case by the probability that it is inconsistent with its temporal
context. The feature extraction mirrors the training features exactly, using the
configured embedding provider for the context similarity signals. If the model
file is absent, callers fall back to the unsupervised neighbour distance score.
"""
from __future__ import annotations

import math
import os
from datetime import datetime

from app.core.logging import logger
from app.ml.registry import get_embedding_provider

_K = 4
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "consistency_model.joblib")
_bundle = None
_load_tried = False


def available() -> bool:
    return _load()[0] is not None


def _load():
    global _bundle, _load_tried
    if not _load_tried:
        _load_tried = True
        try:
            import joblib  # local import so the API starts even without sklearn
            _bundle = joblib.load(_MODEL_PATH)
            logger.info("tamper model loaded", extra={"action": "model_load"})
        except Exception as exc:  # noqa: BLE001
            logger.info(f"tamper model unavailable: {exc}", extra={"action": "model_load"})
            _bundle = None
    return _bundle, _MODEL_PATH


def _parse(ts):
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(str(ts))
    except Exception:
        return None


def _features_for_case(records: list) -> list[list[float]]:
    provider = get_embedding_provider()
    rows = sorted(records, key=lambda r: (r.timestamp is None, r.timestamp or datetime.min))
    n = len(rows)
    embs = [r.embedding if r.embedding else provider.embed_text(r.content or "") for r in rows]
    times = [_parse(r.timestamp) for r in rows]
    apps = [r.source_app or "" for r in rows]
    dominant = max(set(apps), key=apps.count) if apps else ""
    order = sorted(range(n), key=lambda i: (times[i] or datetime.min))
    rank = [0] * n
    for k, i in enumerate(order):
        rank[i] = k
    gaps = [abs((times[i] - times[i - 1]).total_seconds())
            for i in range(1, n) if times[i] and times[i - 1]]
    med = sorted(gaps)[len(gaps) // 2] if gaps else 300.0

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    feats = []
    for i in range(n):
        lo, hi = max(0, i - _K), min(n, i + _K + 1)
        neigh = [j for j in range(lo, hi) if j != i]
        sims = [dot(embs[i], embs[j]) for j in neigh] or [0.0]
        mean_s = sum(sims) / len(sims)
        std_s = (sum((s - mean_s) ** 2 for s in sims) / len(sims)) ** 0.5
        gp = abs((times[i] - times[i - 1]).total_seconds()) if i > 0 and times[i] and times[i - 1] else med
        gn = abs((times[i + 1] - times[i]).total_seconds()) if i + 1 < n and times[i] and times[i + 1] else med
        ob = 0
        if times[i]:
            if i > 0 and times[i - 1] and times[i] < times[i - 1]:
                ob = 1
            if i + 1 < n and times[i + 1] and times[i] > times[i + 1]:
                ob = 1
        sender = rows[i].sender or ""
        prev_sender = rows[i - 1].sender if i > 0 else sender
        foreign = 1 if (sender.startswith("+") and not sender.startswith("+91")) else 0
        content = rows[i].content or ""
        m = rows[i].modality.value if hasattr(rows[i].modality, "value") else str(rows[i].modality)
        feats.append([
            float(mean_s), float(min(sims)), float(std_s),
            math.log1p(gp), math.log1p(gn), float(ob), abs(rank[i] - i) / max(1, n),
            1.0 if apps[i] != dominant else 0.0, float(foreign),
            1.0 if sender != prev_sender else 0.0,
            1.0 if m == "CHAT" else 0.0, 1.0 if m == "CALL" else 0.0,
            1.0 if m == "IMAGE" else 0.0, 1.0 if m == "METADATA" else 0.0,
            min(len(content), 400) / 400.0,
            1.0 if any(c.isdigit() for c in content) else 0.0,
            1.0 if ("0x" in content or "http" in content or "bc1" in content) else 0.0,
        ])
    return rows, feats


def score_case(records: list) -> dict[str, float] | None:
    """Return {artifact_id: probability of inconsistency}, or None if no model."""
    bundle, _ = _load()
    if bundle is None or not records:
        return None
    rows, feats = _features_for_case(records)
    probs = bundle["model"].predict_proba(feats)[:, 1]
    return {rows[i].id: round(float(probs[i]), 4) for i in range(len(rows))}
