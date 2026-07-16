"""Build the largest feasible labelled training corpus for the consistency model.

Two data sources are combined to maximise volume and realism:
  1. Every authentic text corpus available in the project (the prior chat
     datasets and sample investigative chats) is harvested into a message pool.
  2. A large synthetic multimodal UFDR corpus is generated on top of that pool:
     many cases, each an ordered timeline of chat, call, image and metadata
     artifacts with realistic timestamps, applications and participants. A
     labelled taxonomy of manipulations (timestamp shift, metadata substitution,
     image replacement, artifact deletion) is injected so that every artifact
     carries a ground truth tamper label for supervised training.

The output is a single JSON lines file where each row is one artifact with its
case, its neighbours and its label. Increasing --cases increases the data volume,
which the training curve shows improves accuracy.
"""
import argparse
import csv
import glob
import json
import os
import random
from datetime import datetime, timedelta

HERE = os.path.dirname(__file__)
# repo root that holds the sibling datasets (works from the backend/training dir)
CANDIDATES = [
    os.path.abspath(os.path.join(HERE, "..", "..", "..", "Summarizer", "Dataset")),
    os.path.abspath(os.path.join(HERE, "..", "..", "..", "Agentic", "data")),
    "/sessions/dazzling-cool-goldberg/mnt/Mini Project/Summarizer/Dataset",
    "/sessions/dazzling-cool-goldberg/mnt/Mini Project/Agentic/data",
]

APPS = ["WhatsApp", "Signal", "Telegram", "Messenger", "SMS", "Instagram"]
HOME_NUMS = [f"+9198{random.randint(10**7, 10**8 - 1)}" for _ in range(60)]
FOREIGN_NUMS = [f"+1{random.randint(10**9, 10**10 - 1)}" for _ in range(20)]
CRYPTO = ["0x52908400098527886E0F7030069857D2E4169EE7",
          "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
          "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"]
IMAGE_CAPTIONS = ["photo of a sedan near the dock", "screenshot of a bank transfer",
                  "picture of a handover", "image of a warehouse door", "selfie at a cafe",
                  "photo of a parcel", "map screenshot", "picture of cash on a table"]


def _harvest_messages() -> list[str]:
    pool: list[str] = []
    for base in CANDIDATES:
        if not os.path.isdir(base):
            continue
        for path in glob.glob(os.path.join(base, "*")):
            try:
                if path.endswith(".json"):
                    doc = json.load(open(path, encoding="utf-8"))
                    stack = [doc]
                    while stack:
                        cur = stack.pop()
                        if isinstance(cur, dict):
                            for k in ("text", "message", "content", "body"):
                                if isinstance(cur.get(k), str) and cur[k].strip():
                                    pool.append(cur[k].strip())
                            stack.extend(cur.values())
                        elif isinstance(cur, list):
                            stack.extend(cur)
                        elif isinstance(cur, str) and len(cur.strip()) > 1 and len(cur) < 400:
                            pool.append(cur.strip())
                elif path.endswith(".csv"):
                    for row in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
                        for k, v in row.items():
                            if v and isinstance(v, str) and 1 < len(v) < 400 and " " in v:
                                pool.append(v.strip())
                elif path.endswith(".txt"):
                    for line in open(path, encoding="utf-8", errors="replace"):
                        line = line.split(":", 1)[-1].strip()
                        if 1 < len(line) < 400:
                            pool.append(line)
            except Exception:
                continue
    # de duplicate while keeping order
    seen, out = set(), []
    for m in pool:
        if m.lower() not in seen:
            seen.add(m.lower())
            out.append(m)
    return out


def _rand_msg(pool, rng):
    return rng.choice(pool) if pool else "meet me later"


def build(cases: int, seed: int, out_path: str) -> dict:
    rng = random.Random(seed)
    pool = _harvest_messages()
    n_written = 0
    tamper_counts = {"none": 0, "timestamp_shift": 0, "metadata_substitution": 0,
                     "image_replacement": 0, "artifact_deletion": 0}

    with open(out_path, "w", encoding="utf-8") as fh:
        for c in range(cases):
            case_id = f"case_{c:05d}"
            length = rng.randint(15, 60)
            t0 = datetime(2024, 1, 1) + timedelta(days=rng.randint(0, 400), hours=rng.randint(0, 23))
            home = rng.choice(HOME_NUMS)
            peer = rng.choice(HOME_NUMS + FOREIGN_NUMS)
            app = rng.choice(APPS)
            t = t0
            artifacts = []
            for i in range(length):
                # advance time by a realistic gap
                t = t + timedelta(minutes=rng.choice([1, 2, 3, 5, 8, 13, 21, 34, 60, 120]))
                roll = rng.random()
                if roll < 0.7:
                    modality, content = "CHAT", _rand_msg(pool, rng)
                    if rng.random() < 0.04:
                        content += " send to " + rng.choice(CRYPTO)
                elif roll < 0.82:
                    modality, content = "CALL", f"call {rng.choice(['outgoing','incoming'])} {rng.randint(10,600)}s"
                elif roll < 0.94:
                    modality, content = "IMAGE", rng.choice(IMAGE_CAPTIONS)
                else:
                    modality, content = "METADATA", f"location ping {rng.uniform(8,13):.4f},{rng.uniform(76,80):.4f}"
                artifacts.append({
                    "idx": i, "modality": modality, "content": content,
                    "sender": home if i % 2 == 0 else peer,
                    "recipient": peer if i % 2 == 0 else home,
                    "app": app, "timestamp": t.isoformat(),
                    "true_time": t.isoformat(), "tamper": "none",
                })

            # inject labelled tampering into a fraction of artifacts
            n_tamper = max(1, int(length * rng.uniform(0.08, 0.18)))
            targets = rng.sample(range(length), n_tamper)
            for j in targets:
                kind = rng.choice(["timestamp_shift", "metadata_substitution",
                                   "image_replacement", "artifact_deletion"])
                a = artifacts[j]
                if kind == "timestamp_shift":
                    shifted = datetime.fromisoformat(a["timestamp"]) + timedelta(
                        hours=rng.choice([-72, -48, -24, 24, 48, 72]))
                    a["timestamp"] = shifted.isoformat()
                elif kind == "metadata_substitution":
                    a["app"] = rng.choice([x for x in APPS if x != a["app"]])
                    a["sender"] = rng.choice(FOREIGN_NUMS)
                elif kind == "image_replacement":
                    a["modality"] = "IMAGE"
                    a["content"] = _rand_msg(pool, rng)  # a caption that does not fit an image slot
                elif kind == "artifact_deletion":
                    a["_delete"] = True  # this artifact is removed from the case
                    # the gap becomes detectable at the surviving neighbour
                    nb = j + 1 if j + 1 < length else j - 1
                    if 0 <= nb < length and not artifacts[nb].get("_delete"):
                        artifacts[nb]["tamper"] = "artifact_deletion"
                    continue
                a["tamper"] = kind

            for a in artifacts:
                if a.get("_delete"):
                    continue  # the deleted artifact is physically absent (the gap)
                label = 0 if a["tamper"] == "none" else 1
                tamper_counts[a["tamper"]] += 1
                fh.write(json.dumps({
                    "case_id": case_id, "idx": a["idx"], "modality": a["modality"],
                    "content": a["content"], "sender": a["sender"], "recipient": a["recipient"],
                    "app": a["app"], "timestamp": a["timestamp"],
                    "label": label, "tamper": a["tamper"],
                }) + "\n")
                n_written += 1

    return {"artifacts": n_written, "cases": cases, "authentic_messages": len(pool),
            "tamper_counts": tamper_counts, "out": out_path}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(HERE, "corpus.jsonl"))
    args = ap.parse_args()
    stats = build(args.cases, args.seed, args.out)
    print(json.dumps(stats, indent=2))
