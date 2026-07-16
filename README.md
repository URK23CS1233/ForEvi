# ForEvi — Forensic Evidence Intelligence

**Agentic AI-Based Investigation of Universal Forensic Extraction Device Reports (UFDR) Using Cross-Modal Evidence Correlation**

Sprint 1 delivers the platform foundation: futuristic web home page, authentication with admin approval, role-based access control (4 roles), and a tamper-evident (hash-chained) audit trail. All data flows exclusively through the REST API.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 (async) · PostgreSQL · PyJWT · Argon2id |
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS v4 · Framer Motion |
| Security | JWT access+refresh (rotation), RBAC, login rate-limit, hash-chained audit log, strict CORS, security headers |

Roles: `ADMIN` · `INVESTIGATING_OFFICER` · `FORENSIC_ANALYST` · `AUDITOR`.
New registrations start as `PENDING` until an admin approves them.

## Run on Windows

### 1. Database (once)
Open psql (or pgAdmin) on your existing PostgreSQL and run:
```sql
CREATE DATABASE forevi;
```

### 2. Backend
```powershell
cd "C:\Karunya\Mini Project\ForEvi\backend"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env → set DATABASE_URL password, and a fresh SECRET_KEY:
#   python -c "import secrets; print(secrets.token_hex(32))"
python seed_admin.py
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/api/docs

### 3. Frontend (new terminal)
```powershell
cd "C:\Karunya\Mini Project\ForEvi\frontend"
npm install
npm run dev
```
Open http://localhost:5173 — the Vite dev server proxies `/api/*` to the backend.

### 4. First login
- Admin: `admin@forevi.in` / `ChangeMe@123` (from `.env`; change it immediately)
- Register a test officer at `/register`, approve it in **Access Control**, then sign in with it.

## Tests
```powershell
cd backend
pytest        # 11 tests: auth flow, RBAC gates, refresh rotation, audit chain
```

## API surface (Sprint 1)
```
POST /api/v1/auth/register     create account (status=PENDING)
POST /api/v1/auth/login        JWT pair (rate-limited)
POST /api/v1/auth/refresh      rotate refresh token
POST /api/v1/auth/logout       revoke refresh token
GET  /api/v1/auth/me           current user
GET  /api/v1/users             list users            [ADMIN, AUDITOR]
PATCH /api/v1/users/{id}       approve/disable/role  [ADMIN]
GET  /api/v1/users/audit/log   audit trail           [ADMIN, AUDITOR]
GET  /api/v1/users/audit/verify recompute hash chain [ADMIN, AUDITOR]
GET  /api/v1/health, /health/db
```

## Audit chain (forensic-grade logging)
Every security event is appended with `entry_hash = SHA-256(prev_hash | ts | actor | action | resource | detail | ip)`. Rows are never updated or deleted; `GET /users/audit/verify` recomputes the whole chain — any retroactive edit flips `chain_intact` to `false`. This is the same integrity principle the platform will later apply to evidence artifacts.

## Roadmap
- Sprint 2 — Case workspace + UFDR ingestion (evidence records, media/EXIF extraction, chain of custody)
- Sprint 3 — Hybrid retrieval (BGE-M3 + pgvector) + natural-language agent console (integrates the Phase-2 chat summarizer)
- Sprint 4 — Cross-modal correlation, Evidence Consistency Score, gap detection, grounded reports

---

## Production build (features, realtime, trained model)

This build turns the platform into a working forensic tool.

### New capabilities
- **Cases**: create and browse isolated evidence workspaces.
- **UFDR ingestion**: upload JSON, XML, CSV or SQLite exports; a background job
  parses, normalizes, hashes, extracts entities and embeds every record.
- **Realtime**: an authenticated WebSocket streams live ingestion progress and
  notifications with no page refresh (in memory by default, Redis backed for
  multiple replicas).
- **Deterministic entity extraction**: validated cryptocurrency addresses,
  E.164 phone numbers with foreign flagging, hashes, e-mails and links.
- **Search**: keyword, semantic (embedding) and entity modes.
- **Consistency and tamper scoring**: a trained model scores each artifact
  against its temporal context and flags contextual inconsistency.

### Trained consistency and tamper model
Trained on a labelled multimodal corpus of 55,414 artifacts across 1,500 cases
(built from every authentic dataset in the project plus a synthesized, labelled
tamper taxonomy). Measured on a case disjoint test set:

| Metric | Value |
|---|---|
| AUROC | 0.9952 |
| Average precision | 0.9806 |
| F1 | 0.9065 |
| Precision / Recall | 0.861 / 0.957 |

Per class recall: timestamp shift 0.98, metadata substitution 1.00, image
replacement 0.93, artifact deletion 0.91. The data scaling study shows accuracy
rising with data volume (test AUROC 0.986 at 105 cases to 0.994 at 1,050 cases),
so training on more data on your workstation raises accuracy further. See
`backend/training/README.md` to regenerate data and retrain at larger scale.

### Run with Docker
```bash
cd ForEvi
docker compose up --build          # db, redis, api (seeds admin), web on :8080
```

### Run natively (as before)
Backend `uvicorn app.main:app --reload`, frontend `npm run dev`. The dashboard
now has a Cases section; open a case to ingest a UFDR and watch progress live.
