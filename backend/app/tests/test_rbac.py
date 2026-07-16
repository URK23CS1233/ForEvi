"""RBAC tests: role gates on admin endpoints, approval flow end-to-end."""
import pytest

from app.tests.conftest import register_and_activate

pytestmark = pytest.mark.asyncio


async def _admin(client) -> dict:
    """Create an ACTIVE admin directly (seed path) and return tokens."""
    from app.core.security import hash_password
    from app.db.base import SessionLocal
    from app.db.models import Role, User, UserStatus

    async with SessionLocal() as db:
        db.add(User(email="admin@forevi.in", full_name="Admin",
                    password_hash=hash_password("Adm1nPass!123"),
                    role=Role.ADMIN, status=UserStatus.ACTIVE))
        await db.commit()
    r = await client.post("/api/v1/auth/login", json={"email": "admin@forevi.in", "password": "Adm1nPass!123"})
    assert r.status_code == 200
    return r.json()


async def test_non_admin_cannot_list_users(client):
    tokens = await register_and_activate(client, "io2@nia.gov.in")
    r = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 403


async def test_admin_approves_pending_user(client):
    admin_tokens = await _admin(client)
    await client.post("/api/v1/auth/register", json={
        "email": "newio@nia.gov.in", "full_name": "New IO", "password": "Str0ngPass!123",
    })
    users = (await client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_tokens['access_token']}"})).json()
    target = next(u for u in users if u["email"] == "newio@nia.gov.in")
    assert target["status"] == "PENDING"

    r = await client.patch(f"/api/v1/users/{target['id']}",
                           json={"status": "ACTIVE"},
                           headers={"Authorization": f"Bearer {admin_tokens['access_token']}"})
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"

    r = await client.post("/api/v1/auth/login", json={"email": "newio@nia.gov.in", "password": "Str0ngPass!123"})
    assert r.status_code == 200


async def test_admin_cannot_disable_self(client):
    admin_tokens = await _admin(client)
    me = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_tokens['access_token']}"})).json()
    r = await client.patch(f"/api/v1/users/{me['id']}",
                           json={"status": "DISABLED"},
                           headers={"Authorization": f"Bearer {admin_tokens['access_token']}"})
    assert r.status_code == 400


async def test_audit_endpoints_gated_and_verify(client):
    admin_tokens = await _admin(client)
    r = await client.get("/api/v1/users/audit/verify",
                         headers={"Authorization": f"Bearer {admin_tokens['access_token']}"})
    assert r.status_code == 200
    assert r.json()["chain_intact"] is True
