"""Database models: identity, audit, and forensic case data."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer,
                        JSON, String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- identity
class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    INVESTIGATING_OFFICER = "INVESTIGATING_OFFICER"
    FORENSIC_ANALYST = "FORENSIC_ANALYST"
    AUDITOR = "AUDITOR"


class UserStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=32), default=Role.INVESTIGATING_OFFICER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus, native_enum=False, length=16), default=UserStatus.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    """Append only, hash chained, tamper evident audit trail."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


# --------------------------------------------------------------------------- forensic
class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class Modality(str, enum.Enum):
    CHAT = "CHAT"
    CALL = "CALL"
    IMAGE = "IMAGE"
    CONTACT = "CONTACT"
    FILE = "FILE"
    METADATA = "METADATA"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus, native_enum=False, length=16), default=CaseStatus.OPEN, nullable=False)
    artifact_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    __table_args__ = (Index("ix_evidence_case_modality", "case_id", "modality"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    modality: Mapped[Modality] = mapped_column(Enum(Modality, native_enum=False, length=16), nullable=False)
    source_app: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    sender: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    raw: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    consistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MediaMetadata(Base):
    __tablename__ = "media_metadata"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    artifact_id: Mapped[str] = mapped_column(String(32), ForeignKey("evidence_records.id", ondelete="CASCADE"), index=True, nullable=False)
    exif: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    gps_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    camera: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    capture_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EntityType(str, enum.Enum):
    CRYPTO = "CRYPTO"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    URL = "URL"
    HASH = "HASH"
    IMEI = "IMEI"


class EntityHit(Base):
    __tablename__ = "entity_hits"
    __table_args__ = (Index("ix_entity_case_type", "case_id", "entity_type"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(32), ForeignKey("evidence_records.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, native_enum=False, length=16), nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    is_foreign: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, native_enum=False, length=16), default=JobStatus.QUEUED, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="info", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
