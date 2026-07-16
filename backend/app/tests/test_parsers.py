"""UFDR parser tests across formats."""
import json

from app.services.parsers import parse


def test_json_list():
    data = json.dumps([{"message": "hello", "sender": "A", "app": "WhatsApp"}]).encode()
    recs = parse("x.json", data)
    assert recs and recs[0]["content"] == "hello" and recs[0]["source_app"] == "WhatsApp"


def test_json_dict_of_lists():
    data = json.dumps({"chats": [{"text": "hi"}], "calls": [{"content": "ring"}]}).encode()
    recs = parse("x.json", data)
    assert len(recs) == 2


def test_csv():
    data = b"content,sender,app\nhello there,Bob,Signal\n"
    recs = parse("x.csv", data)
    assert recs[0]["content"] == "hello there" and recs[0]["sender"] == "Bob"


def test_xml():
    data = b"<root><msg sender='A'>hi there</msg></root>"
    recs = parse("x.xml", data)
    assert any(r["content"] == "hi there" for r in recs)


def test_content_sniff_json():
    recs = parse("noext", b'[{"text":"sniffed"}]')
    assert recs[0]["content"] == "sniffed"
