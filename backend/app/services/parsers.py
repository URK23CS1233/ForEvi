"""Format tolerant UFDR parsers.

Each parser normalizes a heterogeneous export into a uniform list of records,
where every record carries a modality, a content payload, participants, an
optional timestamp and the original row preserved under `raw`.
"""
import csv
import io
import json
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
from typing import Any

MODALITIES = {"CHAT", "CALL", "IMAGE", "CONTACT", "FILE", "METADATA"}


def _rec(modality="CHAT", content="", sender="", recipient="", source_app="",
         timestamp=None, raw=None) -> dict:
    m = (modality or "CHAT").upper()
    if m not in MODALITIES:
        m = "CHAT"
    return {"modality": m, "content": content or "", "sender": sender or "",
            "recipient": recipient or "", "source_app": source_app or "",
            "timestamp": timestamp, "raw": raw or {}}


def _from_obj(obj: dict) -> dict:
    g = lambda *ks: next((str(obj[k]) for k in ks if obj.get(k) not in (None, "")), "")
    content = g("content", "message", "text", "body", "value", "snippet")
    return _rec(
        modality=g("modality", "type", "category") or "CHAT",
        content=content,
        sender=g("sender", "from", "author", "source", "number_from"),
        recipient=g("recipient", "to", "destination", "number_to"),
        source_app=g("app", "application", "source_app", "platform"),
        timestamp=g("timestamp", "time", "date", "datetime") or None,
        raw=obj,
    )


def parse_json(data: bytes) -> list[dict]:
    doc = json.loads(data.decode("utf-8", errors="replace"))
    rows: list[Any] = []
    if isinstance(doc, list):
        rows = doc
    elif isinstance(doc, dict):
        # a single top level container list takes precedence
        primary = next((doc[k] for k in ("records", "messages", "data", "items", "artifacts")
                        if isinstance(doc.get(k), list)), None)
        if primary is not None:
            rows = list(primary)
        else:
            # otherwise merge every list valued field (e.g. {chats: [...], calls: [...]})
            for v in doc.values():
                if isinstance(v, list):
                    rows.extend(v)
            if not rows:
                rows = [doc]
    return [_from_obj(r) if isinstance(r, dict) else _rec(content=str(r)) for r in rows]


def parse_csv(data: bytes) -> list[dict]:
    text = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [_from_obj({k: v for k, v in row.items() if k}) for row in reader]


def parse_xml(data: bytes) -> list[dict]:
    root = ET.fromstring(data.decode("utf-8", errors="replace"))
    rows = []
    for el in root.iter():
        if el is root:
            continue
        obj = {**el.attrib}
        if el.text and el.text.strip():
            obj["content"] = el.text.strip()
        if len(obj) > 0:
            rows.append(_from_obj(obj))
    return [r for r in rows if r["content"] or r["sender"] or r["recipient"]]


def parse_sqlite(data: bytes) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tf:
        tf.write(data)
        tf.flush()
        con = sqlite3.connect(tf.name)
        con.row_factory = sqlite3.Row
        rows = []
        try:
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                try:
                    for r in con.execute(f'SELECT * FROM "{t}" LIMIT 100000').fetchall():
                        obj = dict(r)
                        obj.setdefault("source_app", t)
                        rows.append(_from_obj(obj))
                except sqlite3.Error:
                    continue
        finally:
            con.close()
    return rows


def parse(filename: str, data: bytes) -> list[dict]:
    name = (filename or "").lower()
    if name.endswith(".json"):
        return parse_json(data)
    if name.endswith(".csv") or name.endswith(".tsv"):
        return parse_csv(data)
    if name.endswith(".xml"):
        return parse_xml(data)
    if name.endswith((".sqlite", ".db", ".sqlite3")):
        return parse_sqlite(data)
    # content sniff fallback
    head = data[:64].lstrip()
    if head.startswith(b"{") or head.startswith(b"["):
        return parse_json(data)
    if head.startswith(b"<"):
        return parse_xml(data)
    if data[:16] == b"SQLite format 3\x00":
        return parse_sqlite(data)
    return parse_csv(data)
