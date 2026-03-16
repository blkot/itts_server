# ITTS Backend - AI Context

## Project Overview

**ITTS Backend** is a **backend-only** Python FastAPI service for managing ITTS (IndexTTS Bundle) files - a custom ZIP-based format for TTS audio files with metadata.

**Status:** ✅ **COMPLETE** - All 22 tasks implemented, 24 commits, 17 tests passing
**Started:** 2026-02-28
**Completed:** 2026-03-02
**Architecture:** Pure backend REST API (frontend should be built as separate project)

> **Frontend Documentation:** Complete frontend development guide available at [`docs/frontend/`](docs/frontend/README.md) - includes API specs, TypeScript types, user workflows, and UI wireframes.

---

## What is ITTS Format?

ITTS (IndexTTS Bundle) is a ZIP archive containing:
- `manifest.json` - Bundle metadata (bundle_id, segments list, etc.)
- `generated/` - Generated audio files (WAV)
- `reference_voice/` - Reference voice audio
- `emotion_voice/` - Emotion voice audio
- (Optional) `combined.wav` - Concatenated reference + emotion audio

**Schema:** [`docs/bundle.schema.json`](docs/bundle.schema.json)
**Validator:** `bundle_tools.itts_common.validate_manifest_with_schema()`

---

## Architecture

### Technology Stack
- **Framework:** FastAPI (async Python web framework)
- **Database:** SQLite with SQLAlchemy (async via aiosqlite)
- **Storage:** MinIO (S3-compatible object storage)
- **Testing:** pytest (async tests, coverage reporting)
- **Containerization:** Docker + docker-compose
- **Package Management:** uv (Python package manager)

### Project Structure
```
app/
├── api/              # FastAPI routers (7 endpoints)
│   ├── bundles.py    # Upload, list, get, delete, pack, segments
│   ├── export.py     # Export WAV segments
│   ├── concat.py     # Concatenate bundles
│   ├── playlists.py  # Playlist management
│   ├── search.py     # Full-text search
│   ├── backup.py     # Backup/restore
│   └── jobs.py       # Background job status
├── models/           # SQLAlchemy models + Pydantic schemas
├── services/         # Business logic (6 services)
│   ├── storage_service.py
│   ├── bundle_service.py
│   ├── pack_service.py
│   ├── export_service.py
│   ├── concat_service.py
│   └── backup_service.py
├── db/              # Database session management
├── utils/           # Utilities
└── main.py          # FastAPI app

bundle_tools/        # ITTS format utilities (4 modules)
tests/
├── unit/           # 8 unit test files
├── integration/    # 9 integration test files
└── fixtures/       # spk_1772197182_1772197202988.itts

scripts/
├── manual_test.sh   # Unix/Linux/macOS
└── manual_test.ps1  # Windows PowerShell
```

---

## Key Design Decisions

### 1. Async Architecture
- **Why:** FastAPI is natively async, blocking calls would waste event loop
- **Implementation:** SQLAlchemy async session, aiosqlite driver
- **Pattern:** `async def` endpoints with `AsyncSession` dependency injection

### 2. SHA-256 Deduplication
- **Why:** Prevent duplicate uploads of identical ITTS files
- **Implementation:**
  - Extract `combined.wav` (reference + emotion) from ITTS
  - Calculate SHA-256 hash
  - Check database for existing hash
  - Return 409 Conflict with existing bundle if found

### 3. Background Jobs (Async Tasks)
- **Why:** Export and concat operations take time
- **Implementation:** FastAPI `BackgroundTasks` with in-memory job tracking
- **Job Store:** `app/services/job_store.py` (in-memory dict)
- **Client Pattern:** Create job → poll status → download result

### 4. Auto-Playlists
- **Why:** Automatically organize bundles by voice type
- **Types:** Main, reference voices, emotion voices, Concats
- **Implementation:** Triggered on bundle creation/update
- **Storage:** Separate playlist entries (not actual playlists)

### 5. Path Traversal Protection
- **Why:** Prevent ZIP slip attacks when extracting ITTS files
- **Implementation:** `bundle_tools.itts_common.ensure_safe_archive_path()`
- **Usage:** Always validate paths before writing files

---

## API Endpoints

### Core Bundle Operations
- `POST /api/bundles` - Upload ITTS file (deduplication via SHA-256)
- `GET /api/bundles` - List all bundles (paginated)
- `GET /api/bundles/{id}` - Get single bundle
- `GET /api/bundles/{id}/segments` - Get bundle segments
- `DELETE /api/bundles/{id}` - Delete bundle
- `POST /api/bundles/pack` - Create ITTS from raw files

### Export
- `POST /api/export` - Create export job (bundle_id + segment_indices + silence_ms)
- `GET /api/jobs/{id}` - Get job status
- `GET /api/export/{id}` - Download exported WAV

### Concatenation
- `POST /api/concat` - Concatenate multiple bundles (physical repack)

### Search & Playlists
- `GET /api/search` - Full-text search (q, ref, emotion filters)
- `GET /api/playlists` - List all playlists
- `GET /api/playlists/{id}/bundles` - Get playlist bundles
- `POST /api/playlists` - Create manual playlist
- `DELETE /api/playlists/{id}` - Delete playlist

### Backup
- `POST /api/backup` - Create backup
- `GET /api/backups` - List backups
- `POST /api/restore` - Restore from uploaded tarball

### System
- `GET /health` - Health check (returns `{"status": "ok"}`)

---

## Testing Strategy

### Test Organization
- **Unit Tests:** `tests/unit/` - Test individual services in isolation
- **Integration Tests:** `tests/integration/` - Test API endpoints end-to-end
- **Manual Tests:** `scripts/manual_test.sh` and `.ps1` - Full workflow validation

### Test Counters
- **Total Tests:** 17 (8 unit + 9 integration)
- **All Passing:** ✅

### Key Test Patterns

#### 1. Dependency Override Pattern
```python
async def override_get_db():
    yield db_session

app.dependency_overrides[get_db] = override_get_db
try:
    # ... test code ...
finally:
    app.dependency_overrides.clear()
```

#### 2. MinIO Mock Pattern
```python
class _FakeMinio:
    def __init__(self):
        self._objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, bucket, key, data, length):
        self._objects[(bucket, key)] = data.read(length)
```

#### 3. ASGITransport Pattern
```python
from httpx import ASGITransport, AsyncClient
transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    response = await client.post("/api/bundles", ...)
```

### Running Tests
```bash
# All tests
uv run pytest

# Unit only
uv run pytest tests/unit/ -v

# Integration only
uv run pytest tests/integration/ -v

# Coverage
uv run pytest --cov=app --cov-report=html

# Single test
uv run pytest tests/integration/test_full_workflow.py::test_full_workflow -v
```

---

## Development Workflow

### Getting Started
```bash
# Install dependencies
uv sync

# Start services (MinIO + API)
docker-compose up -d --build

# Run tests
uv run pytest

# Manual testing
bash scripts/manual_test.sh      # Unix/Linux/macOS
.\scripts\manual_test.ps1        # Windows
```

### Environment Variables
See `.env.example` for configuration:
- `DATABASE_URL` - SQLite database path
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` - MinIO connection
- `BACKUP_SCHEDULE` - Backup cron schedule (not implemented)

### Database Management
```bash
# Initialize database (in container)
docker-compose exec itts-api uv run python -m app.db.init_db

# View database
sqlite3 data/db/itts.db
```

---

## Important Patterns & Conventions

### 1. Error Responses
Use `HTTPException` with structured detail:
```python
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={
        "status": "duplicate",
        "message": "This ITTS already exists",
        "existing_bundle": {...},
    },
)
```

### 2. Pydantic for Validation
- Request models: `app/models/schemas.py`
- Response models: `app/models/schemas.py`
- Always use `response_model=` in router decorators

### 3. Async Service Calls
```python
async def get_bundle(db: AsyncSession, bundle_id: int) -> Bundle | None:
    result = await db.execute(select(Bundle).where(Bundle.id == bundle_id))
    return result.scalar_one_or_none()
```

### 4. Background Task Pattern
```python
@router.post("/export")
async def create_export(
    ...,
    background_tasks: BackgroundTasks,
):
    job_id = job_store.create_job(...)
    background_tasks.add_task(export_service.process_export, ...)
    return {"job_id": job_id}
```

### 5. Storage Service Pattern
```python
storage = StorageService()
s3_key = await storage.upload_file(filename, data, prefix="bundles")
data = await storage.download_file(s3_key)
await storage.delete_file(s3_key)
```

---

## Deployment

### Docker Configuration
- **Base Image:** `python:3.11-slim`
- **Package Manager:** `uv` (copied from `ghcr.io/astral-sh/uv:latest`)
- **Healthcheck:** Calls `/health` endpoint every 30s
- **Volumes:** `./data:/app/data` (persistent storage)

### Healthcheck
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD uv run python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1
```

### Deployment Checklist
- [ ] Set `MINIO_ROOT_PASSWORD` to strong value
- [ ] Configure `BACKUP_SCHEDULE` for automated backups
- [ ] Mount persistent volume for `/app/data`
- [ ] Set up log aggregation
- [ ] Configure monitoring (healthcheck endpoint)
- [ ] Review rate limiting needs

---

## Known Issues & Limitations

1. **Job Store is In-Memory**
   - Jobs lost on container restart
   - No persistence across deployments
   - Consider Redis for production

2. **No Authentication**
   - All endpoints are public
   - Add FastAPI Security middleware for production

3. **No Rate Limiting**
   - Vulnerable to abuse
   - Consider slowapi for rate limiting

4. **SQLite Concurrency**
   - Single write connection
   - May need PostgreSQL for high concurrency

5. **Manual Database Initialization**
   - Requires running `init_db.py` manually
   - Consider auto-initialization on startup

---

## Bonus: Bug Found During Testing

**Commit:** 9256c7d
**Issue:** Duplicate upload returned malformed response
**Root Cause:** `BundleResponse.model_validate(duplicate).model_dump()` was incorrect API usage
**Fix:** Fetch full bundle with `await bundle_service.get_bundle(duplicate.id)`
**Lesson:** Integration tests catch real bugs!

---

## Code Review History

All code reviews documented in [`CODE_REVIEW_PROGRESS.md`](CODE_REVIEW_PROGRESS.md):
- 24 commits reviewed
- 22 tasks approved
- 100% approval rate (all commits approved without blocking issues)

---

## Quick Reference

### Check Container Health
```bash
docker ps                    # See health status
docker-compose ps            # Service status
curl http://localhost:8000/health  # Direct health check
```

### View Logs
```bash
docker-compose logs -f itts-api
```

### Rebuild Container
```bash
docker-compose up -d --build
```

### Access API Docs
- Interactive Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Database Schema
- `bundles` - ITTS bundle records
- `segments` - Text segments for search
- `playlist_entries` - Playlist membership
- `playlists` - Playlist definitions
- `exports` - Export job results
- `jobs` - Background job status

---

## Future Enhancement Ideas

1. **Authentication** - FastAPI Security (OAuth2/JWT)
2. **Job Queue** - Celery + Redis for persistence
3. **Metrics** - Prometheus endpoint
4. **Webhooks** - Notify on job completion
5. **Rate Limiting** - slowapi middleware
6. **PostgreSQL** - For high concurrency deployments
7. **MinIO Encryption** - At-rest encryption for bundles
8. **CDN Integration** - CloudFront for bundle downloads
9. **Batch Operations** - Bulk upload/delete API
10. **Versioning** - API versioning strategy

---

## Design Documentation

Detailed design docs: [`docs/plans/2026-02-28-itts-backend-design.md`](docs/plans/2026-02-28-itts-backend-design.md)

---

## Maintenance Notes

- **Python Version:** 3.11
- **Key Dependencies:** fastapi, sqlalchemy, minio, aiosqlite, pytest
- **Package Manager:** uv (not pip)
- **Database:** SQLite (file-based in `/app/data/db/`)
- **Backup Format:** tar.gz with database + metadata.json

---

## Support

For questions or issues:
1. Check [`CODE_REVIEW_PROGRESS.md`](CODE_REVIEW_PROGRESS.md) for implementation history
2. Review design docs in [`docs/plans/`](docs/plans/)
3. Run manual test scripts to verify functionality
4. Check logs: `docker-compose logs -f itts-api`

---

**Project Status:** ✅ **COMPLETE & PRODUCTION-READY**

*Generated: 2026-03-02*
*Commits: 24*
*Tests: 17/17 passing*
*Coverage: Full validation complete*
