"""Ingestion pipeline with live progress.

Parses an uploaded UFDR file, normalizes it into evidence records, extracts
deterministic entities, computes an embedding through the configured provider,
and emits progress events over the realtime bus after every batch. Runs as a
background task so the upload request returns immediately with a job id.
"""
import hashlib
from datetime import datetime, timezone

from dateutil import parser as dateparser  # type: ignore
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import bus, case_channel, user_channel
from app.core.logging import logger
from app.db.base import SessionLocal
from app.db.models import (Case, EntityHit, EntityType, EvidenceRecord, IngestionJob,
                          JobStatus, Modality, Notification)
from app.ml.registry import get_embedding_provider
from app.services import entities as ent
from app.services import parsers


def _parse_ts(value):
    if not value:
        return None
    try:
        dt = dateparser.parse(str(value))
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


async def _emit(job: IngestionJob, status: str):
    await bus.publish(case_channel(job.case_id), {
        "type": "ingestion_progress", "job_id": job.id, "case_id": job.case_id,
        "status": status, "progress": job.progress, "processed": job.processed,
        "total": job.total, "message": job.message,
    })


async def run_ingestion(job_id: str, filename: str, data: bytes) -> None:
    provider = get_embedding_provider()
    async with SessionLocal() as db:
        job = await db.get(IngestionJob, job_id)
        if job is None:
            return
        try:
            records = parsers.parse(filename, data)
            job.total = len(records)
            job.status = JobStatus.RUNNING
            job.message = f"parsed {len(records)} records"
            await db.commit()
            await _emit(job, "running")

            batch = 0
            for i, r in enumerate(records):
                content = r["content"]
                sha = hashlib.sha256(
                    (content + r["sender"] + r["recipient"]).encode("utf-8", "replace")
                ).hexdigest()
                rec = EvidenceRecord(
                    case_id=job.case_id,
                    modality=Modality(r["modality"]) if r["modality"] in Modality.__members__ else Modality.CHAT,
                    source_app=r["source_app"][:120],
                    sender=r["sender"][:255],
                    recipient=r["recipient"][:255],
                    content=content,
                    timestamp=_parse_ts(r["timestamp"]),
                    sha256=sha,
                    raw=r["raw"] if isinstance(r["raw"], dict) else {},
                    embedding=provider.embed_text(content) if content else None,
                )
                db.add(rec)
                await db.flush()
                for e in ent.extract(" ".join([content, r["sender"], r["recipient"]])):
                    db.add(EntityHit(
                        case_id=job.case_id, artifact_id=rec.id,
                        entity_type=EntityType(e.entity_type), value=e.value[:512],
                        normalized=e.normalized[:512], is_foreign=e.is_foreign))
                batch += 1
                if batch >= 25 or i == len(records) - 1:
                    job.processed = i + 1
                    job.progress = int((i + 1) * 100 / max(1, len(records)))
                    await db.commit()
                    await _emit(job, "running")
                    batch = 0

            await db.execute(update(Case).where(Case.id == job.case_id).values(
                artifact_count=Case.artifact_count + len(records)))
            job.status = JobStatus.DONE
            job.progress = 100
            job.message = f"ingested {len(records)} records"
            job.finished_at = datetime.now(timezone.utc)
            db.add(Notification(user_id=job.created_by, kind="success",
                                title="Ingestion complete",
                                body=f"{filename}: {len(records)} records added to the case."))
            await db.commit()
            await _emit(job, "done")
            await bus.publish(user_channel(job.created_by), {
                "type": "notification", "kind": "success",
                "title": "Ingestion complete", "body": f"{filename}: {len(records)} records."})
            logger.info("ingestion done", extra={"job_id": job.id, "case_id": job.case_id})
        except Exception as exc:  # noqa: BLE001
            job.status = JobStatus.FAILED
            job.message = f"failed: {exc}"[:500]
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await _emit(job, "failed")
            logger.exception("ingestion failed", extra={"job_id": job_id})
