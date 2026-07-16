"""Feature engineering for the consistency and tamper detection model.

Each artifact is described by how well it agrees with its temporal context:
embedding similarity to neighbours, temporal ordering consistency, metadata
agreement with the dominant application of the case, participant characteristics,
modality, and lightweight content signals. These are exactly the cross modal
context features that make contextual tampering detectable where a per artifact
view cannot see it.
"""
import math
import os
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.ml.stub import StubEmbeddingProvider  # noqa: E402

_PROVIDER = StubEmbeddingProvider()
K = 4
FEATURE_NAMES = [
    "emb_ctx_sim", "emb_ctx_min", "emb_ctx_std",
    "gap_prev_log", "gap_next_log", "order_break", "time_rank_resid",
    "app_mismatch", "sender_foreign", "sender_switch",
    "is_chat", "is_call", "is_image", "is_meta",
    "content_len", "has_digits", "has_link_or_addr",
]


def _emb(text):
    return np.array(_PROVIDER.embed_text(text or ""), dtype=np.float32)


def _parse(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def features_for_case(rows: list[dict]) -> tuple[np.ndarray, list[int], list[str]]:
    """Return (X, labels, tamper_types) for one case, ordered by idx."""
    rows = sorted(rows, key=lambda r: r["idx"])
    n = len(rows)
    embs = [_emb(r["content"]) for r in rows]
    times = [_parse(r["timestamp"]) for r in rows]
    apps = [r.get("app", "") for r in rows]
    dominant_app = max(set(apps), key=apps.count) if apps else ""
    # ranking of artifacts by timestamp; residual vs true index reveals shifts
    order = sorted(range(n), key=lambda i: (times[i] or datetime.min))
    time_rank = [0] * n
    for rank, i in enumerate(order):
        time_rank[i] = rank
    gaps = []
    for i in range(n):
        if i > 0 and times[i] and times[i - 1]:
            gaps.append(abs((times[i] - times[i - 1]).total_seconds()))
    med_gap = float(np.median(gaps)) if gaps else 300.0

    X, labels, ttypes = [], [], []
    for i in range(n):
        lo, hi = max(0, i - K), min(n, i + K + 1)
        neigh = [j for j in range(lo, hi) if j != i]
        sims = [float(np.dot(embs[i], embs[j])) for j in neigh] or [0.0]
        gp = abs((times[i] - times[i - 1]).total_seconds()) if i > 0 and times[i] and times[i - 1] else med_gap
        gn = abs((times[i + 1] - times[i]).total_seconds()) if i + 1 < n and times[i] and times[i + 1] else med_gap
        order_break = 0
        if times[i]:
            if i > 0 and times[i - 1] and times[i] < times[i - 1]:
                order_break = 1
            if i + 1 < n and times[i + 1] and times[i] > times[i + 1]:
                order_break = 1
        sender = rows[i].get("sender", "")
        prev_sender = rows[i - 1].get("sender", "") if i > 0 else sender
        foreign = 1 if (sender.startswith("+") and not sender.startswith("+91")) else 0
        content = rows[i].get("content", "")
        m = rows[i]["modality"]
        X.append([
            float(np.mean(sims)), float(np.min(sims)), float(np.std(sims)),
            math.log1p(gp), math.log1p(gn), float(order_break),
            abs(time_rank[i] - i) / max(1, n),
            1.0 if apps[i] != dominant_app else 0.0,
            float(foreign),
            1.0 if sender != prev_sender else 0.0,
            1.0 if m == "CHAT" else 0.0, 1.0 if m == "CALL" else 0.0,
            1.0 if m == "IMAGE" else 0.0, 1.0 if m == "METADATA" else 0.0,
            min(len(content), 400) / 400.0,
            1.0 if any(ch.isdigit() for ch in content) else 0.0,
            1.0 if ("0x" in content or "http" in content or "bc1" in content) else 0.0,
        ])
        labels.append(int(rows[i]["label"]))
        ttypes.append(rows[i].get("tamper", "none"))
    return np.array(X, dtype=np.float32), labels, ttypes


def build_matrix(rows_by_case: dict[str, list[dict]]):
    Xs, ys, ts, cids = [], [], [], []
    for cid, rows in rows_by_case.items():
        X, y, tt = features_for_case(rows)
        Xs.append(X); ys.extend(y); ts.extend(tt); cids.extend([cid] * len(y))
    return np.vstack(Xs), np.array(ys), ts, cids
