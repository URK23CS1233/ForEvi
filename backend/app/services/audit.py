"""Append-only hash-chained audit writer.

Every security-relevant event is chained to the previous one:
    entry_hash = sha256(prev_hash | timestamp | actor | action | resource | detail | ip)
Verification walks the chain and recomputes hashes; a single altered row
invalidates the rest of the chain. Original rows are never updated or deleted.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import sha256_hex
from app.db.models import AuditLog

GENESIS = "0" * 64


async def record(
    db: AsyncSession,
    *,
    action: str,
    actor_id: str | None = None,
    actor_email: str | None = None,
    resource: str = "",
    detail: dict | None = None,
    ip_address: str = "",
) -> AuditLog:
    last = (
        await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(1))
    ).scalar_one_or_none()
    prev_hash = last.entry_hash if last else GENESIS

    created_at = datetime.now(timezone.utc)
    detail_str = json.dumps(detail or {}, sort_keys=True, separators=(",", ":"))
    payload = "|".join([
        prev_hash,
        created_at.isoformat(),
        actor_id or "-",
        action,
        resource,
        detail_str,
        ip_address,
    ])
    entry = AuditLog(
        created_at=created_at,
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource=resource,
        detail=detail_str,
        ip_address=ip_address,
        prev_hash=prev_hash,
        entry_hash=sha256_hex(payload),
    )
    db.add(entry)
    await db.flush()
    return entry


async def verify_chain(db: AsyncSession) -> tuple[bool, int]:
    """Recompute the whole chain. Returns (ok, entries_checked)."""
    rows = (await db.execute(select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc()))).scalars().all()
    prev = GENESIS
    for row in rows:
        ts = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
        payload = "|".join([
            prev,
            ts.isoformat(),
            row.actor_id or "-",
            row.action,
            row.resource,
            row.detail,
            row.ip_address,
        ])
        if row.prev_hash != prev or row.entry_hash != sha256_hex(payload):
               return False, len(rows)
        prev = row.entry_hash
    return True, len(rows)
