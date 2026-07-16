"""Seed the super-admin account (idempotent).

Usage:  python seed_admin.py
Reads ADMIN_EMAIL / ADMIN_PASSWORD from .env.
"""
import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine
from app.db.models import Role, User, UserStatus
from app.services import audit


async def main() -> None:
    s = get_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        existing = (await db.execute(select(User).where(User.email == s.admin_email.lower()))).scalar_one_or_none()
        if existing:
            print(f"Admin already exists: {existing.email} (status={existing.status.value})")
            return
        user = User(
            email=s.admin_email.lower(),
            full_name="ForEvi Administrator",
            password_hash=hash_password(s.admin_password),
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()
        await audit.record(db, action="SYSTEM_SEED_ADMIN", actor_id=user.id, actor_email=user.email,
                           resource=f"user:{user.id}")
        await db.commit()
        print(f"Seeded admin: {user.email}  — change the password after first login.")


if __name__ == "__main__":
    asyncio.run(main())
