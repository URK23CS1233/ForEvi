"""Train the tamper and consistency detector and measure real accuracy.

Features are extracted once and cached, then reused for the case disjoint
train, validation and test splits and for the data scaling study, so the whole
run stays fast on a CPU. Class imbalance is handled with sample weights and a
small hyperparameter search selects the best configuration.
"""
import argparse
import json
import os
from collections import defaultdict

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (average_precision_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
import joblib

from features import FEATURE_NAMES, features_for_case

HERE = os.path.dirname(__file__)


def load_rows(path):
    by_case = defaultdict(list)
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        by_case[r["case_id"]].append(r)
    return by_case


def build_all(by_case):
    """Extract features once for every case; return arrays plus a case index."""
    Xs, ys, tts, cids = [], [], [], []
    for cid, rows in by_case.items():
        X, y, tt = features_for_case(rows)
        Xs.append(X); ys.append(np.array(y)); tts.append(np.array(tt, dtype=object))
        cids.append(np.array([cid] * len(y), dtype=object))
    return (np.vstack(Xs), np.concatenate(ys), np.concatenate(tts), np.concatenate(cids))


def train_one(Xtr, ytr, params):
    w = np.where(ytr == 1, (ytr == 0).sum() / max(1, (ytr == 1).sum()), 1.0)
    m = HistGradientBoostingClassifier(random_state=0, **params)
    m.fit(Xtr, ytr, sample_weight=w)
    return m


def evaluate(model, X, y, tt):
    prob = model.predict_proba(X)[:, 1]
    pred = (prob >= 0.5).astype(int)
    per = {}
    for cls in ["timestamp_shift", "metadata_substitution", "image_replacement", "artifact_deletion"]:
        mask = tt == cls
        if mask.sum():
            per[cls] = round(float((pred[mask] == 1).mean()), 4)
    return {
        "auroc": round(float(roc_auc_score(y, prob)), 4),
        "auprc": round(float(average_precision_score(y, prob)), 4),
        "f1": round(float(f1_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred)), 4),
        "positives": int(y.sum()), "total": int(len(y)),
        "per_class_recall": per,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join(HERE, "corpus.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "consistency_model.joblib"))
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--max-cases", type=int, default=0, help="0 = use all")
    args = ap.parse_args()

    by_case = load_rows(args.corpus)
    if args.max_cases:
        keep = list(by_case)[: args.max_cases]
        by_case = {c: by_case[c] for c in keep}
    X, y, tt, cid = build_all(by_case)
    print(f"features built: {X.shape[0]} artifacts, {X.shape[1]} features")

    rng = np.random.default_rng(args.seed)
    cases = np.array(sorted(by_case.keys()))
    rng.shuffle(cases)
    n = len(cases)
    tr_ids = set(cases[: int(n * 0.7)])
    va_ids = set(cases[int(n * 0.7): int(n * 0.85)])
    te_ids = set(cases[int(n * 0.85):])
    tr = np.array([c in tr_ids for c in cid]); va = np.array([c in va_ids for c in cid]); te = np.array([c in te_ids for c in cid])
    print(f"train {tr.sum()}  val {va.sum()}  test {te.sum()}")

    grid = [
        {"max_iter": 200, "learning_rate": 0.1, "l2_regularization": 1.0},
        {"max_iter": 300, "learning_rate": 0.08, "max_leaf_nodes": 63, "l2_regularization": 1.0},
    ]
    best, best_auc, best_params = None, -1, None
    for params in grid:
        m = train_one(X[tr], y[tr], params)
        auc = roc_auc_score(y[va], m.predict_proba(X[va])[:, 1])
        print(f"  {params} -> val AUROC {auc:.4f}")
        if auc > best_auc:
            best_auc, best_params = auc, params

    trva = tr | va
    final = train_one(X[trva], y[trva], best_params)
    test_metrics = evaluate(final, X[te], y[te], tt[te])
    print("TEST:", json.dumps(test_metrics))

    # data scaling study over cached features
    tr_case_list = list(tr_ids)
    rng.shuffle(tr_case_list)
    scaling = []
    for frac in (0.1, 0.25, 0.5, 1.0):
        keep = set(tr_case_list[: max(2, int(len(tr_case_list) * frac))])
        sel = np.array([c in keep for c in cid])
        m = train_one(X[sel], y[sel], best_params)
        auc = float(roc_auc_score(y[te], m.predict_proba(X[te])[:, 1]))
        scaling.append({"train_cases": len(keep), "train_artifacts": int(sel.sum()), "test_auroc": round(auc, 4)})
        print(f"  scaling cases={len(keep)} -> test AUROC {auc:.4f}")

    joblib.dump({"model": final, "feature_names": FEATURE_NAMES, "params": best_params,
                 "threshold": 0.5}, args.out)
    report = {"best_params": best_params, "val_auroc": round(float(best_auc), 4),
              "test": test_metrics, "scaling": scaling}
    json.dump(report, open(os.path.join(HERE, "metrics.json"), "w"), indent=2)
    print("saved ->", args.out)


if __name__ == "__main__":
    main()
