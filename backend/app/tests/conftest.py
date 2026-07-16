"""Test fixtures: isolated SQLite database + httpx client against the app."""
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_forevi.db"
os.environ["SECRET_KEY"] = "test-secret"

import asyncio  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.base import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    from app.api.v1.auth import _attempts

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    _attempts.clear()  # reset in-memory login rate limiter between tests
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_and_activate(client: AsyncClient, email: str, role: str = "INVESTIGATING_OFFICER") -> dict:
    """Helper: register a user, flip to ACTIVE directly in DB, login, return tokens."""
    from sqlalchemy import update

    from app.db.base import SessionLocal
    from app.db.models import User, UserStatus

    r = await client.post("/api/v1/auth/register", json={
        "email": email, "full_name": "Test User", "password": "Str0ngPass!123", "requested_role": role,
    })
    assert r.status_code == 201, r.text
    async with SessionLocal() as db:
        await db.execute(update(User).where(User.email == email).values(status=UserStatus.ACTIVE))
        await db.commit()
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass!123"})
    assert r.status_code == 200, r.text
    return r.json()
