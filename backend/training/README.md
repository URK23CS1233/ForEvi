# Consistency and Tamper Model Training

This directory trains the supervised tamper and consistency detector used by the
platform to score how well each artifact agrees with its temporal context.

## Data

`generate_dataset.py` builds the largest feasible labelled corpus. It harvests
every authentic text corpus available in the project and then synthesises a
large multimodal UFDR corpus of many cases, injecting a labelled taxonomy of
manipulations (timestamp shift, metadata substitution, image replacement,
artifact deletion). Increasing `--cases` increases the data volume, which the
scaling study shows improves accuracy.

```bash
python generate_dataset.py --cases 4000 --out corpus.jsonl   # more cases = more data = higher accuracy
```

## Train

```bash
python train_consistency.py --corpus corpus.jsonl            # uses the full corpus
```

The script splits by case so no case appears in both train and test, handles
class imbalance with sample weights, runs a small hyperparameter search, writes
`consistency_model.joblib` and `metrics.json`, and prints a data scaling study.

## Ship

Copy the trained model into the API so it is used at inference:

```bash
cp consistency_model.joblib metrics.json ../app/ml/models/
```

The `POST /api/v1/cases/{id}/consistency` endpoint then reports
`method: trained_model`, and `GET /api/v1/cases/model/info` returns the metrics.

## Scaling to higher accuracy on your workstation

- Generate more cases (`--cases 8000` or more) to use more data.
- Swap the stub embedding provider for a real multilingual text encoder and an
  image encoder, then retrain so the context similarity features carry semantic
  meaning; this is expected to raise accuracy further on real extractions.
- The same pipeline runs on a GPU with a larger corpus and more boosting
  iterations without any code change.
