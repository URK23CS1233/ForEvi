"""Auth flow tests: register→pending, approval gate, login, refresh rotation, audit chain."""
import pytest

from app.tests.conftest import register_and_activate

pytestmark = pytest.mark.asyncio


async def test_register_creates_pending_user(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "io@nia.gov.in", "full_name": "IO Kumar",
        "password": "Str0ngPass!123", "requested_role": "INVESTIGATING_OFFICER",
    })
    assert r.status_code == 201
    assert r.json()["status"] == "PENDING"


async def test_pending_user_cannot_login(client):
    await client.post("/api/v1/auth/register", json={
        "email": "pending@nia.gov.in", "full_name": "Pending User", "password": "Str0ngPass!123",
    })
    r = await client.post("/api/v1/auth/login", json={"email": "pending@nia.gov.in", "password": "Str0ngPass!123"})
    assert r.status_code == 403
    assert "approval" in r.json()["detail"].lower()


async def test_admin_role_cannot_be_self_registered(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "evil@x.com", "full_name": "Evil", "password": "Str0ngPass!123", "requested_role": "ADMIN",
    })
    assert r.status_code == 400


async def test_login_and_me(client):
    tokens = await register_and_activate(client, "active@nia.gov.in")
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "active@nia.gov.in"


async def test_wrong_password_rejected(client):
    await register_and_activate(client, "wp@nia.gov.in")
    r = await client.post("/api/v1/auth/login", json={"email": "wp@nia.gov.in", "password": "WrongPass!123"})
    assert r.status_code == 401


async def test_refresh_rotation_revokes_old_token(client):
    tokens = await register_and_activate(client, "rot@nia.gov.in")
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r1.status_code == 200
    # the old refresh token must now be unusable
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401
    # the new one works
    r3 = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1.json()["refresh_token"]})
    assert r3.status_code == 200


async def test_audit_chain_verifies(client):
    await register_and_activate(client, "audit@nia.gov.in")
    from app.db.base import SessionLocal
    from app.services.audit import verify_chain

    async with SessionLocal() as db:
        ok, checked = await verify_chain(db)
    assert ok is True
    assert checked >= 2  # register + login at minimum
