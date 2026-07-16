"""Schemas for cases, evidence, jobs and notifications."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(default="", max_length=4000)


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: str
    owner_id: str
    status: str
    artifact_count: int
    created_at: datetime


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    modality: str
    source_app: str
    sender: str
    recipient: str
    content: str
    timestamp: datetime | None
    sha256: str
    consistency_score: float | None
    created_at: datetime


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    artifact_id: str
    entity_type: str
    value: str
    normalized: str
    is_foreign: bool


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    filename: str
    status: str
    progress: int
    total: int
    processed: int
    message: str
    created_at: datetime
    finished_at: datetime | None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    title: str
    body: str
    read: bool
    created_at: datetime


class SearchResult(BaseModel):
    query: str
    mode: str
    total: int
    results: list[EvidenceOut]
