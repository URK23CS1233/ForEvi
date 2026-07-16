"""Admin endpoints: list users, approve/disable, change roles; auditor view of audit chain."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import client_ip, require_roles
from app.db.base import get_db
from app.db.models import Role, User, UserStatus
from app.schemas.auth import AuditEntryOut, UserAdminUpdate, UserOut
from app.services import audit
from app.db.models import AuditLog

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    _: User = Depends(require_roles(Role.ADMIN, Role.AUDITOR)),
    db: AsyncSession = Depends(get_db),
):
    return (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserAdminUpdate,
    request: Request,
    admin: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and body.status in (UserStatus.DISABLED, UserStatus.PENDING):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot disable your own account")

    changes: dict = {}
    if body.role is not None and body.role != user.role:
        changes["role"] = {"from": user.role.value, "to": body.role.value}
        user.role = body.role
    if body.status is not None and body.status != user.status:
        changes["status"] = {"from": user.status.value, "to": body.status.value}
        user.status = body.status

    if changes:
        await audit.record(
            db, action="USER_ADMIN_UPDATE", actor_id=admin.id, actor_email=admin.email,
            resource=f"user:{user.id}", detail=changes, ip_address=client_ip(request),
        )
        await db.commit()
    return user


@router.get("/audit/log", response_model=list[AuditEntryOut])
async def audit_log(
    _: User = Depends(require_roles(Role.ADMIN, Role.AUDITOR)),
    db: AsyncSession = Depends(get_db),
    limit: int = 200,
):
    rows = (
        await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 1000)))
    ).scalars().all()
    return rows


@router.get("/audit/verify")
async def audit_verify(
    _: User = Depends(require_roles(Role.ADMIN, Role.AUDITOR)),
    db: AsyncSession = Depends(get_db),
):
    ok, checked = await audit.verify_chain(db)
    return {"chain_intact": ok, "entries_checked": checked}
