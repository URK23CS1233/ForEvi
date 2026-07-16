"""Case, ingestion, evidence, search and realtime tests."""
import asyncio
import json

import pytest

from app.tests.conftest import register_and_activate

pytestmark = pytest.mark.asyncio

SAMPLE = json.dumps([
    {"message": "meet at dock 7 friday, send to 0x52908400098527886E0F7030069857D2E4169EE7",
     "sender": "+919812345678", "recipient": "+14155552671", "app": "WhatsApp", "time": "2024-05-01T20:00:00Z"},
    {"message": "understood", "sender": "+14155552671", "app": "WhatsApp", "time": "2024-05-01T20:05:00Z"},
    {"type": "IMAGE", "content": "photo of a car", "app": "Gallery", "time": "2024-05-01T21:00:00Z"},
]).encode()


async def _wait_job(client, case_id, headers, tries=40):
    for _ in range(tries):
        jobs = (await client.get(f"/api/v1/cases/{case_id}/jobs", headers=headers)).json()
        if jobs and jobs[0]["status"] in ("DONE", "FAILED"):
            return jobs[0]
        await asyncio.sleep(0.05)
    return None


async def test_case_lifecycle_and_ingestion(client):
    tok = await register_and_activate(client, "io@nia.gov.in", "INVESTIGATING_OFFICER")
    h = {"Authorization": f"Bearer {tok['access_token']}"}

    r = await client.post("/api/v1/cases", json={"title": "Operation Dock", "description": "test"}, headers=h)
    assert r.status_code == 201
    cid = r.json()["id"]

    r = await client.post(f"/api/v1/cases/{cid}/upload", headers=h,
                          files={"file": ("evidence.json", SAMPLE, "application/json")})
    assert r.status_code == 202

    job = await _wait_job(client, cid, h)
    assert job and job["status"] == "DONE" and job["total"] == 3

    ev = (await client.get(f"/api/v1/cases/{cid}/evidence", headers=h)).json()
    assert len(ev) == 3

    ents = (await client.get(f"/api/v1/cases/{cid}/entities?entity_type=CRYPTO", headers=h)).json()
    assert any(e["entity_type"] == "CRYPTO" for e in ents)

    foreign = (await client.get(f"/api/v1/cases/{cid}/entities?entity_type=PHONE&foreign_only=true", headers=h)).json()
    assert any(e["is_foreign"] for e in foreign)


async def test_search_modes(client):
    tok = await register_and_activate(client, "io2@nia.gov.in", "INVESTIGATING_OFFICER")
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    cid = (await client.post("/api/v1/cases", json={"title": "Search"}, headers=h)).json()["id"]
    await client.post(f"/api/v1/cases/{cid}/upload", headers=h, files={"file": ("e.json", SAMPLE, "application/json")})
    await _wait_job(client, cid, h)

    kw = (await client.get(f"/api/v1/cases/{cid}/search?q=dock&mode=keyword", headers=h)).json()
    assert kw["total"] >= 1
    sem = (await client.get(f"/api/v1/cases/{cid}/search?q=car photo&mode=semantic", headers=h)).json()
    assert sem["mode"] == "semantic" and sem["total"] >= 1


async def test_consistency_scoring(client):
    tok = await register_and_activate(client, "an@nia.gov.in", "FORENSIC_ANALYST")
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    cid = (await client.post("/api/v1/cases", json={"title": "Consistency"}, headers=h)).json()["id"]
    await client.post(f"/api/v1/cases/{cid}/upload", headers=h, files={"file": ("e.json", SAMPLE, "application/json")})
    await _wait_job(client, cid, h)
    r = await client.post(f"/api/v1/cases/{cid}/consistency", headers=h)
    assert r.status_code == 200 and r.json()["scored"] == 3


async def test_auditor_cannot_create_case(client):
    tok = await register_and_activate(client, "aud@nia.gov.in", "AUDITOR")
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    r = await client.post("/api/v1/cases", json={"title": "No"}, headers=h)
    assert r.status_code == 403


async def test_consistency_uses_trained_model(client):
    tok = await register_and_activate(client, "an2@nia.gov.in", "FORENSIC_ANALYST")
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    cid = (await client.post("/api/v1/cases", json={"title": "Model"}, headers=h)).json()["id"]
    await client.post(f"/api/v1/cases/{cid}/upload", headers=h, files={"file": ("e.json", SAMPLE, "application/json")})
    await _wait_job(client, cid, h)
    r = await client.post(f"/api/v1/cases/{cid}/consistency", headers=h)
    assert r.status_code == 200
    assert r.json()["method"] == "trained_model"          # the joblib model is loaded and used

    info = (await client.get("/api/v1/cases/model/info", headers=h)).json()
    assert info["trained_model_loaded"] is True
    assert info["metrics"]["test"]["auroc"] > 0.9         # real measured accuracy is shipped
