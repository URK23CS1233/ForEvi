"""Case management, UFDR ingestion, evidence retrieval, search and consistency."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import client_ip, get_current_user
from app.db.base import get_db
from app.db.models import (Case, CaseStatus, EntityHit, EntityType, EvidenceRecord,
                          IngestionJob, JobStatus, Modality, Role, User)
from app.ml.registry import cosine, get_embedding_provider
from app.schemas.cases import (CaseCreate, CaseOut, EntityOut, EvidenceOut, JobOut, SearchResult)
from app.services import audit
from app.services.ingest import run_ingestion

router = APIRouter(prefix="/cases", tags=["cases"])

WRITE_ROLES = {Role.ADMIN, Role.INVESTIGATING_OFFICER, Role.FORENSIC_ANALYST}
SEE_ALL = {Role.ADMIN, Role.AUDITOR, Role.FORENSIC_ANALYST}


def _require_write(user: User) -> None:
    if user.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This role cannot modify cases")


async def _get_case(db: AsyncSession, case_id: str, user: User) -> Case:
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if user.role not in SEE_ALL and case.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this case")
    return case


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(body: CaseCreate, request: Request,
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _require_write(user)
    case = Case(title=body.title.strip(), description=body.description, owner_id=user.id)
    db.add(case)
    await db.flush()
    await audit.record(db, action="CASE_CREATE", actor_id=user.id, actor_email=user.email,
                       resource=f"case:{case.id}", detail={"title": case.title}, ip_address=client_ip(request))
    await db.commit()
    return case


@router.get("", response_model=list[CaseOut])
async def list_cases(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Case).order_by(Case.created_at.desc())
    if user.role not in SEE_ALL:
        stmt = stmt.where(Case.owner_id == user.id)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _get_case(db, case_id, user)


@router.post("/{case_id}/upload", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_ufdr(case_id: str, request: Request, background: BackgroundTasks,
                      file: UploadFile, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    case = await _get_case(db, case_id, user)
    _require_write(user)
    data = await file.read()
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds the upload limit")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    job = IngestionJob(case_id=case.id, filename=file.filename or "upload", status=JobStatus.QUEUED,
                       created_by=user.id)
    db.add(job)
    await db.flush()
    await audit.record(db, action="UFDR_UPLOAD", actor_id=user.id, actor_email=user.email,
                       resource=f"case:{case.id}", detail={"filename": job.filename, "bytes": len(data)},
                       ip_address=client_ip(request))
    await db.commit()
    background.add_task(run_ingestion, job.id, job.filename, data)
    return job


@router.get("/{case_id}/jobs", response_model=list[JobOut])
async def list_jobs(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_case(db, case_id, user)
    return (await db.execute(select(IngestionJob).where(IngestionJob.case_id == case_id)
                             .order_by(IngestionJob.created_at.desc()))).scalars().all()


@router.get("/{case_id}/evidence", response_model=list[EvidenceOut])
async def list_evidence(case_id: str, modality: str | None = None, limit: int = 100, offset: int = 0,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_case(db, case_id, user)
    stmt = select(EvidenceRecord).where(EvidenceRecord.case_id == case_id)
    if modality and modality.upper() in Modality.__members__:
        stmt = stmt.where(EvidenceRecord.modality == Modality(modality.upper()))
    stmt = stmt.order_by(EvidenceRecord.timestamp.is_(None), EvidenceRecord.timestamp.asc()).limit(min(limit, 500)).offset(offset)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{case_id}/entities", response_model=list[EntityOut])
async def list_entities(case_id: str, entity_type: str | None = None, foreign_only: bool = False,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_case(db, case_id, user)
    stmt = select(EntityHit).where(EntityHit.case_id == case_id)
    if entity_type and entity_type.upper() in EntityType.__members__:
        stmt = stmt.where(EntityHit.entity_type == EntityType(entity_type.upper()))
    if foreign_only:
        stmt = stmt.where(EntityHit.is_foreign.is_(True))
    return (await db.execute(stmt.limit(1000))).scalars().all()


@router.get("/{case_id}/search", response_model=SearchResult)
async def search(case_id: str, q: str = Query(min_length=1), mode: str = "keyword", limit: int = 50,
                 user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_case(db, case_id, user)
    limit = min(limit, 200)
    if mode == "semantic":
        provider = get_embedding_provider()
        qv = provider.embed_text(q)
        rows = (await db.execute(select(EvidenceRecord).where(
            EvidenceRecord.case_id == case_id, EvidenceRecord.embedding.is_not(None)))).scalars().all()
        scored = sorted(rows, key=lambda r: cosine(qv, r.embedding or []), reverse=True)[:limit]
        return SearchResult(query=q, mode="semantic", total=len(scored), results=scored)
    if mode == "entity":
        hits = (await db.execute(select(EntityHit.artifact_id).where(
            EntityHit.case_id == case_id, EntityHit.normalized.ilike(f"%{q}%")))).scalars().all()
        if not hits:
            return SearchResult(query=q, mode="entity", total=0, results=[])
        rows = (await db.execute(select(EvidenceRecord).where(EvidenceRecord.id.in_(hits)).limit(limit))).scalars().all()
        return SearchResult(query=q, mode="entity", total=len(rows), results=rows)
    # keyword (default)
    rows = (await db.execute(select(EvidenceRecord).where(
        EvidenceRecord.case_id == case_id, EvidenceRecord.content.ilike(f"%{q}%")).limit(limit))).scalars().all()
    return SearchResult(query=q, mode="keyword", total=len(rows), results=rows)


@router.post("/{case_id}/consistency", response_model=dict)
async def recompute_consistency(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Score each artifact by how far it sits from its temporal neighbours in
    the current embedding space. Higher scores mark contextual outliers. This
    runs over whichever embedding provider is configured."""
    await _get_case(db, case_id, user)
    _require_write(user)
    rows = (await db.execute(select(EvidenceRecord).where(EvidenceRecord.case_id == case_id)
        .order_by(EvidenceRecord.timestamp.is_(None), EvidenceRecord.timestamp.asc()))).scalars().all()
    if not rows:
        return {"scored": 0, "flagged": 0, "method": "none"}

    # preferred path: the trained tamper model scores each artifact
    from app.ml import tamper
    scores = tamper.score_case(rows)
    if scores is not None:
        flagged = 0
        for r in rows:
            r.consistency_score = scores.get(r.id, 0.0)
            if r.consistency_score >= 0.5:
                flagged += 1
        await db.commit()
        return {"scored": len(rows), "flagged": flagged, "method": "trained_model", "threshold": 0.5}

    # fallback: unsupervised neighbour distance over the current embeddings
    threshold = get_settings().consistency_threshold
    scorable = [r for r in rows if r.embedding]
    K = 4
    flagged = 0
    for i, r in enumerate(scorable):
        lo, hi = max(0, i - K), min(len(scorable), i + K + 1)
        neigh = [scorable[j] for j in range(lo, hi) if j != i]
        if not neigh:
            r.consistency_score = 0.0
            continue
        sims = [cosine(r.embedding, n.embedding) for n in neigh]
        r.consistency_score = round(1.0 - (sum(sims) / len(sims)), 4)
        if r.consistency_score > threshold:
            flagged += 1
    await db.commit()
    return {"scored": len(scorable), "flagged": flagged, "method": "neighbour_distance", "threshold": threshold}


@router.get("/model/info", response_model=dict)
async def model_info(user: User = Depends(get_current_user)):
    """Report whether the trained consistency model is loaded and its test metrics."""
    import json
    import os
    from app.ml import tamper
    metrics = {}
    mp = os.path.join(os.path.dirname(tamper.__file__), "models", "metrics.json")
    if os.path.exists(mp):
        try:
            metrics = json.load(open(mp))
        except Exception:
            metrics = {}
    return {"trained_model_loaded": tamper.available(), "metrics": metrics}
