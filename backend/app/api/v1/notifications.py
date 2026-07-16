"""User notifications."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.base import get_db
from app.db.models import Notification, User
from app.schemas.cases import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def my_notifications(unread_only: bool = False, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read.is_(False))
    return (await db.execute(stmt.order_by(Notification.created_at.desc()).limit(100))).scalars().all()


@router.post("/{nid}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(nid: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    n = await db.get(Notification, nid)
    if n is None or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    n.read = True
    await db.commit()
