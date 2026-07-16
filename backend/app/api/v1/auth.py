"""Authentication endpoints: register (pending approval), login, refresh rotation, logout, me."""
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import client_ip, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    sha256_hex,
    verify_password,
)
from app.db.base import get_db
from app.db.models import RefreshToken, Role, User, UserStatus
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])

# --- tiny in-memory login rate limiter (replaced by Redis in a later sprint) ---
_attempts: dict[str, list[float]] = defaultdict(list)


def _rate_limit(ip: str) -> None:
    s = get_settings()
    now = time.time()
    window = [t for t in _attempts[ip] if now - t < s.login_window_seconds]
    _attempts[ip] = window
    if len(window) >= s.login_max_attempts:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again later.")
    _attempts[ip].append(now)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if body.requested_role == Role.ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admin accounts cannot be self-registered")
    existing = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=body.email.lower(),
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
        role=body.requested_role,
        status=UserStatus.PENDING,
    )
    db.add(user)
    await db.flush()
    await audit.record(
        db, action="AUTH_REGISTER", actor_id=user.id, actor_email=user.email,
        resource=f"user:{user.id}", detail={"requested_role": body.requested_role.value},
        ip_address=client_ip(request),
    )
    await db.commit()
    return user


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = client_ip(request)
    _rate_limit(ip)

    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        await audit.record(db, action="AUTH_LOGIN_FAILED", resource=f"email:{body.email.lower()}", ip_address=ip)
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if user.status == UserStatus.PENDING:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account awaiting administrator approval")
    if user.status == UserStatus.DISABLED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled. Contact an administrator.")

    refresh = create_refresh_token(user.id)
    s = get_settings()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=sha256_hex(refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=s.refresh_token_expire_days),
    ))
    user.last_login_at = datetime.now(timezone.utc)
    await audit.record(db, action="AUTH_LOGIN", actor_id=user.id, actor_email=user.email,
                       resource=f"user:{user.id}", ip_address=ip)
    await db.commit()
    return TokenPair(access_token=create_access_token(user.id, user.role.value), refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, "refresh")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    token_hash = sha256_hex(body.refresh_token)
    record_row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).scalar_one_or_none()
    if record_row is None or record_row.revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked or expired")
    expires_at = record_row.expires_at if record_row.expires_at.tzinfo else record_row.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked or expired")

    user = await db.get(User, payload["sub"])
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account not active")

    # rotation: revoke the used token, issue a new pair
    record_row.revoked = True
    new_refresh = create_refresh_token(user.id)
    s = get_settings()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=sha256_hex(new_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=s.refresh_token_expire_days),
    ))
    await audit.record(db, action="AUTH_REFRESH", actor_id=user.id, actor_email=user.email,
                       resource=f"user:{user.id}", ip_address=client_ip(request))
    await db.commit()
    return TokenPair(access_token=create_access_token(user.id, user.role.value), refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    token_hash = sha256_hex(body.refresh_token)
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).scalar_one_or_none()
    if row:
        row.revoked = True
        await audit.record(db, action="AUTH_LOGOUT", actor_id=row.user_id,
                                           resource=f"user:{row.user_id}", ip_address=client_ip(request))
        await db.commit()


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
