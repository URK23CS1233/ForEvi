"""Pydantic schemas for authentication and users."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import Role, UserStatus


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=10, max_length=128, description="Min 10 chars.")
    requested_role: Role = Role.INVESTIGATING_OFFICER


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    role: Role
    status: UserStatus
    created_at: datetime
    last_login_at: datetime | None


class UserAdminUpdate(BaseModel):
    role: Role | None = None
    status: UserStatus | None = None


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    actor_email: str | None
    action: str
    resource: str
    detail: str
    ip_address: str
    prev_hash: str
    entry_hash: str
