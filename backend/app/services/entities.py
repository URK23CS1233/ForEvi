"""Deterministic forensic entity extraction.

Every extractor is rule based and reproducible, which keeps the answers to
queries such as "chats containing cryptocurrency addresses" or "communications
with foreign numbers" fully auditable and free of any statistical model.
"""
import re
from dataclasses import dataclass

# home country dialing code; numbers outside this are flagged as foreign
HOME_CC = "91"

_ETH = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
_BTC = re.compile(r"\b(?:bc1[a-z0-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
_TRON = re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")
_EMAIL = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_URL = re.compile(r"\bhttps?://[^\s<>\"')]+", re.IGNORECASE)
_HASH = re.compile(r"\b[a-fA-F0-9]{64}\b")
_IMEI = re.compile(r"\b\d{15}\b")
_PHONE = re.compile(r"(?:(?<=\s)|^|[:,>])\+?\d[\d\s().-]{7,17}\d")

_B58 = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")


@dataclass
class Entity:
    entity_type: str
    value: str
    normalized: str = ""
    is_foreign: bool = False


def _valid_base58(s: str) -> bool:
    return all(c in _B58 for c in s)


def _luhn_ok(num: str) -> bool:
    total, alt = 0, False
    for d in reversed(num):
        n = ord(d) - 48
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def _norm_phone(raw: str) -> tuple[str, bool] | None:
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("+"):
        core = digits[1:]
    elif digits.startswith("00"):
        core = digits[2:]
    else:
        core = digits
    if not (8 <= len(core) <= 15):
        return None
    # infer country: leading 91 -> India; otherwise treat prefix as foreign
    if core.startswith(HOME_CC) and len(core) >= 12:
        return "+" + core, False
    if digits.startswith("+") or digits.startswith("00"):
        return "+" + core, not core.startswith(HOME_CC)
    if len(core) == 10:  # bare local number
        return "+" + HOME_CC + core, False
    return "+" + core, not core.startswith(HOME_CC)


def extract(text: str) -> list[Entity]:
    """Return the de duplicated entities found in a text payload."""
    if not text:
        return []
    out: dict[tuple[str, str], Entity] = {}

    def add(t, v, n="", foreign=False):
        out.setdefault((t, n or v), Entity(t, v, n or v, foreign))

    for m in _ETH.findall(text):
        add("CRYPTO", m, m.lower())
    for m in _TRON.findall(text):
        add("CRYPTO", m, m)
    for m in _BTC.findall(text):
        if m.startswith("bc1") or _valid_base58(m):
            add("CRYPTO", m, m)
    for m in _EMAIL.findall(text):
        add("EMAIL", m, m.lower())
    for m in _URL.findall(text):
        add("URL", m, m.rstrip(".,);"))
    for m in _HASH.findall(text):
        add("HASH", m, m.lower())
    for m in _IMEI.findall(text):
        if _luhn_ok(m):
            add("IMEI", m, m)
    for m in _PHONE.findall(text):
        norm = _norm_phone(m.strip())
        if norm:
            add("PHONE", m.strip(), norm[0], norm[1])
    return list(out.values())
