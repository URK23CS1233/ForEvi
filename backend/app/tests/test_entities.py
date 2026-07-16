"""Deterministic entity extraction tests."""
from app.services.entities import extract


def _types(text):
    return {(e.entity_type, e.normalized) for e in extract(text)}


def test_eth_address():
    hits = extract("send to 0x52908400098527886E0F7030069857D2E4169EE7 now")
    assert any(e.entity_type == "CRYPTO" for e in hits)


def test_btc_and_tron():
    hits = extract("wallet 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2 or TRON TJ2j...")
    assert any(e.entity_type == "CRYPTO" and e.value.startswith("1") for e in hits)


def test_foreign_vs_home_number():
    hits = {e.normalized: e.is_foreign for e in extract("call +14155552671 and +919812345678")}
    assert any(v for v in hits.values())            # a foreign number detected
    assert any(not v for v in hits.values())        # a home number detected


def test_email_url_hash():
    t = "mail a@b.com see https://x.io/a hash " + "a" * 64
    kinds = {e.entity_type for e in extract(t)}
    assert {"EMAIL", "URL", "HASH"} <= kinds


def test_empty():
    assert extract("") == []
