# ITTS Backend Design

**Date:** 2026-02-28
**Author:** Claude + User
**Status:** Approved

---

## 1. Overview

A Docker-based backend for managing ITTS (IndexTTS Bundle) files. The system provides library management, custom audio export, bundle concatenation, search, and backup/restore capabilities.

**Scope:**
- Personal audio library for small group (2-5 users)
- No streaming (file export only)
- No authentication for v1 (add later)
- Primary use: backend for future web/mobile player

---

## 2. Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Host                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    docker-compose.yml                       │ │
│  │                                                             │ │
│  │  ┌──────────────────┐         ┌──────────────────┐         │ │
│  │  │   itts-api       │         │     minio        │         │ │
│  │  │   (FastAPI)      │◄────────┤   (S3 API)       │         │ │
│  │  │   Port: 8000     │  S3     │   Port: 9000     │         │ │
│  │  │                  │         │   Port: 9001     │         │ │
│  │  │  • SQLite DB     │         │   (Web UI)       │         │ │
│  │  │  • Bundle tools  │         │                  │         │ │
│  │  │  • Export/Concat │         │  • .itts files   │         │ │
│  │  │  • Backup/Restore│         │  • Export cache  │         │ │
│  │  └──────────────────┘         └──────────────────┘         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

                         Future Clients:
                     ┌─────────┐    ┌──────────┐
                     │ Web App │    │Mobile App│
                     └─────────┘    └──────────┘
```

### 2.2 Technology Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Database | SQLite (with SQLAlchemy) |
| Storage | MinIO (S3-compatible) |
| Container | Docker + docker-compose |
| Package Manager | uv |
| Testing | pytest + httpx |
| Async Jobs | FastAPI BackgroundTasks |

---

## 3. Database Schema

```sql
-- Users (auth added later, schema ready)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ITTS bundles
CREATE TABLE bundles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    s3_key TEXT NOT NULL UNIQUE,
    manifest_json TEXT NOT NULL,

    -- Deduplication
    generated_audio_sha256 TEXT UNIQUE,

    -- Auto-playlist grouping
    reference_voice TEXT,
    emotion_voice TEXT,

    mode TEXT,
    total_duration_ms INTEGER,

    -- Concatenation tracking
    is_concatenated BOOLEAN DEFAULT FALSE,
    source_bundle_ids TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Segments (for mode=segments and mode=both)
CREATE TABLE segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id INTEGER NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL,
    text_prompt TEXT NOT NULL,
    normalized_text TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    filename TEXT,
    sha256 TEXT,
    UNIQUE(bundle_id, segment_index)
);

-- Playlists
CREATE TABLE playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_auto_generated BOOLEAN DEFAULT FALSE,

    -- For auto-playlists
    auto_type TEXT,              -- 'reference' or 'emotion'
    auto_value TEXT,              -- e.g., "Emma" or "Happy"

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Playlist membership
CREATE TABLE playlist_entries (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    bundle_id INTEGER NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(playlist_id, bundle_id)
);

-- Permissions (for future multi-user)
CREATE TABLE permissions (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    can_view BOOLEAN DEFAULT TRUE,
    PRIMARY KEY(playlist_id, user_id)
);

-- Export cache
CREATE TABLE exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id INTEGER NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
    s3_key TEXT NOT NULL UNIQUE,
    segment_indices TEXT NOT NULL,
    join_silence_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Async jobs
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,                  -- 'export' or 'concat'
    status TEXT NOT NULL,                -- 'pending', 'processing', 'completed', 'failed'
    input_params TEXT NOT NULL,
    result_bundle_id INTEGER,
    result_export_id INTEGER,
    error_message TEXT,
    progress REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Full-text search
CREATE VIRTUAL TABLE bundles_fts USING fts5(
    title, text_prompt, normalized_text,
    content=bundles, content_rowid=rowid
);
```

---

## 4. API Endpoints

### 4.1 Bundle Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bundles` | Upload existing .itts file |
| GET | `/api/bundles` | List all bundles (paginated) |
| GET | `/api/bundles/{id}` | Get bundle metadata |
| GET | `/api/bundles/{id}/manifest` | Get raw manifest.json |
| GET | `/api/bundles/{id}/segments` | List segments with text |
| DELETE | `/api/bundles/{id}` | Delete bundle |

### 4.2 Pack API (New)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bundles/pack` | Pack raw files into new ITTS |

**Request format:**
```json
{
  "title": "My Bundle",
  "prompt_text": "Hello world",
  "reference_title": "voice_01",
  "emotion_title": "happy"
}
```

**Files:**
- `generated_combined`: WAV file
- `reference_audio`: WAV file
- `emotion_audio`: WAV file

### 4.3 Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/export` | Create custom segment export (async) |
| GET | `/api/export/{id}` | Download exported WAV |
| GET | `/api/jobs/{id}` | Get job status |

### 4.4 Concatenate

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/concat` | Create concatenated bundle (async) |

### 4.5 Playlists

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/playlists` | List all playlists |
| GET | `/api/playlists/{id}/bundles` | Get bundles in playlist |
| POST | `/api/playlists` | Create manual playlist |
| DELETE | `/api/playlists/{id}` | Delete playlist |

### 4.6 Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search` | Full-text search |
| GET | `/api/search?ref={voice}` | Filter by reference |
| GET | `/api/search?emotion={name}` | Filter by emotion |

### 4.7 Backup & Restore

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/backup` | Trigger manual backup |
| GET | `/api/backups` | List available backups |
| GET | `/api/backups/{filename}` | Download backup |
| POST | `/api/restore` | Restore from backup |

---

## 5. Key Features

### 5.1 Deduplication

- Uses `generated_audio.combined.sha256` as unique key
- Checks for duplicates on both `/api/bundles` and `/api/bundles/pack`
- Returns 409 Conflict with existing bundle info if duplicate found

### 5.2 Auto-Playlists

- **Main playlist:** Contains all bundles
- **Reference playlists:** One per unique `reference_audio.title`
- **Emotion playlists:** One per unique `emotion_audio.title`
- Created automatically on bundle upload

### 5.3 Segment Export

- Select specific segments by index
- Optional silence between segments
- Cached in MinIO to avoid re-processing
- Returns direct WAV download

### 5.4 Concatenation

- Physical repack into new ITTS file (Method 2)
- Creates new bundle with `is_concatenated=true`
- Stores source bundle IDs in `source_bundle_ids`
- Auto-creates "Concats" playlist

### 5.5 Backup & Restore

- **Manual:** Triggered via API
- **Scheduled:** Daily at 2 AM (configurable)
- **Format:** `itts-backup-YYYY-MM-DD.tar.gz`
- **Contents:** SQLite DB + MinIO data + metadata

---

## 6. Async Job Management

Long-running operations (export, concat) use async jobs:

```
Client → POST /api/export → Returns {job_id: 42}
         ↓
         GET /api/jobs/42 → Poll status
         ↓
         {status: 'completed', result: {...}}
         ↓
         GET /api/export/123 → Download file
```

**Status flow:** `pending` → `processing` → `completed` / `failed`

---

## 7. Project Structure

```
itts_server/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── bundles.py             # Bundle CRUD
│   │   ├── playlists.py           # Playlists
│   │   ├── export.py              # Export/concat
│   │   ├── search.py              # Search
│   │   └── backup.py              # Backup/restore
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLAlchemy models
│   │   └── schemas.py             # Pydantic schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── bundle_service.py      # Bundle logic
│   │   ├── export_service.py      # Export/concat
│   │   ├── storage_service.py     # MinIO wrapper
│   │   ├── pack_service.py        # ITTS packing
│   │   ├── dedup_service.py       # Duplicate detection
│   │   └── backup_service.py      # Backup/restore
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py             # DB session
│   │   └── init_db.py             # Create tables
│   └── utils/
│       ├── __init__.py
│       └── minio_client.py        # MinIO wrapper
├── bundle_tools/                  # Existing tools
│   ├── itts_common.py
│   ├── pack_itts.py
│   └── unpack_itts.py
├── tests/
│   ├── fixtures/
│   │   ├── spk_1772197182_1772197202988.itts
│   │   └── spk_1772197204_1772197238887.itts
│   ├── unit/
│   │   ├── test_api_endpoints.py
│   │   ├── test_bundle_service.py
│   │   ├── test_export_service.py
│   │   ├── test_concat_service.py
│   │   ├── test_deduplication.py
│   │   └── test_backup_service.py
│   ├── integration/
│   │   ├── test_upload_workflow.py
│   │   ├── test_export_workflow.py
│   │   └── test_backup_restore.py
│   └── conftest.py
├── scripts/
│   └── manual_test.sh             # Manual test suite
├── docs/
│   └── plans/
│       └── 2026-02-28-itts-backend-design.md
├── data/                          # Git ignored
│   ├── db/itts.db
│   ├── minio/
│   ├── logs/
│   └── backups/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 8. Docker Deployment

### 8.1 docker-compose.yml

```yaml
services:
  itts-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data/db:/app/data
      - ./data/logs:/app/logs
      - ./data/backups:/app/backups
    environment:
      - DATABASE_URL=sqlite:///data/db/itts.db
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
      - MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
      - MINIO_BUCKET=itts-bundles
      - BACKUP_SCHEDULE=0 2 * * *
    depends_on:
      - minio
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ./data/minio:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER:-admin}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-changeme}
    command: server /data --console-address ":9001"
    restart: unless-stopped
```

### 8.2 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite connection string | `sqlite:///data/db/itts.db` |
| `MINIO_ENDPOINT` | MinIO host:port | `minio:9000` |
| `MINIO_ACCESS_KEY` | MinIO username | `admin` |
| `MINIO_SECRET_KEY` | MinIO password | `changeme` |
| `MINIO_BUCKET` | S3 bucket name | `itts-bundles` |
| `BACKUP_SCHEDULE` | Cron schedule | `0 2 * * *` |

---

## 9. Testing Strategy

### 9.1 Unit Tests
- Test each service in isolation
- Mock external dependencies (MinIO, DB)
- Target: >80% coverage for core logic

### 9.2 Integration Tests
- Test full workflows end-to-end
- Use real fixtures from `tests/fixtures/`
- Test DB + MinIO interactions

### 9.3 Manual Tests
- `scripts/manual_test.sh` for validation
- Tests both `/api/bundles` and `/api/bundles/pack`
- Verifies duplicate detection

### 9.4 Test Fixtures

| File | SHA-256 | Purpose |
|------|---------|---------|
| `spk_1772197182_1772197202988.itts` | `19794afc...` | Test `/api/bundles/pack` |
| `spk_1772197204_1772197238887.itts` | `3b9eb259...` | Test `/api/bundles` |

---

## 10. Future Considerations

### 10.1 v2 Features
- User authentication (OAuth or password)
- Streaming endpoints (HTTP Range requests)
- Per-user library isolation
- Admin-controlled permissions

### 10.2 Scalability
- Migrate SQLite → PostgreSQL
- Add Redis for caching
- Separate worker service (Celery)
- CDN for file distribution

### 10.3 Compatibility
- Support ITTS v1.0.0 (missing `playback` field)
- Forward-compatible with future versions
- Schema validation allows unknown fields

---

## 11. Acceptance Criteria

- [ ] Can upload .itts files via `/api/bundles`
- [ ] Can pack raw files via `/api/bundles/pack`
- [ ] Duplicate detection works for both endpoints
- [ ] Can export custom segments as WAV
- [ ] Can concatenate bundles into new ITTS
- [ ] Auto-playlists created on upload
- [ ] Full-text search works
- [ ] Backup and restore functional
- [ ] Unit tests pass with >80% coverage
- [ ] Integration tests pass
- [ ] Manual test script validates all features
- [ ] Docker compose brings up full stack
- [ ] MinIO web UI accessible
- [ ] API documentation (OpenAPI) available

---

## Appendix: ITTS Bundle Format Reference

The ITTS bundle format is defined in:
- `docs/BUNDLE_FORMAT.md` - Format specification
- `docs/bundle.schema.json` - JSON schema
- `bundle_tools/README.md` - Tool usage

Key manifest fields used by backend:
- `generated_audio.combined.sha256` - Deduplication key
- `reference_audio.title` - Auto-playlist grouping
- `emotion_audio.title` - Auto-playlist grouping
- `generated_audio.mode` - Storage pattern
- `prompt.text` - Full-text search
- `prompt.segments` - Segment export options

---

## Appendix: Code Review Guidelines

For AI-assisted implementation, use these review criteria:

### Phase Gate Reviews

**After Phase 1 (Foundation):**
- [ ] `pyproject.toml` has all required dependencies
- [ ] `.gitignore` excludes data/, logs, .env
- [ ] Docker compose builds successfully
- [ ] Health endpoint returns 200 OK

**After Phase 2 (Models):**
- [ ] All tables have proper foreign keys with cascade delete
- [ ] `generated_audio_sha256` has UNIQUE constraint
- [ ] Playlist entry composite PK is correct
- [ ] Tests mock database properly

**After Phase 3 (Services):**
- [ ] Storage service uses async MinIO client
- [ ] Bundle service handles v1.0.0 manifests (missing `playback` field)
- [ ] Deduplication checks happen BEFORE MinIO upload
- [ ] Auto-playlists created within same transaction

**After Phase 4 (API):**
- [ ] All endpoints have proper error handling (404, 409, 422)
- [ ] File uploads limit size (add `UploadFile` size check)
- [ ] Background tasks use FastAPI's `BackgroundTasks`
- [ ] OpenAPI schema is complete

**After Phase 5 (Export/Concat):**
- [ ] Large WAV files stream properly (don't load full file in memory)
- [ ] Job status updates atomically
- [ ] Failed jobs store error messages
- [ ] Export cleanup: delete old exports from MinIO

**After Phase 6 (Remaining):**
- [ ] Search parameter validation (no SQL injection)
- [ ] Backup doesn't expose sensitive data
- [ ] Playlist operations are atomic

### Security Checklist

- [ ] Path traversal protection in ZIP extraction
- [ ] File size limits on uploads (10MB max for .itts)
- [ ] SHA-256 validation prevents tampering
- [ ] No credentials in logs
- [ ] MinIO credentials from environment only
- [ ] SQL injection protection (use SQLAlchemy, not f-strings)

### Performance Checklist

- [ ] Pagination on list endpoints (default page_size=50)
- [ ] Streaming responses for large files
- [ ] Database indexes on:
  - `bundles.generated_audio_sha256`
  - `playlists.name`
  - `playlist_entries(playlist_id, bundle_id)`
- [ ] MinIO presigned URLs for future direct download
- [ ] Connection pooling for SQLite (check_same_thread=False)

### Testing Checklist

- [ ] Unit tests mock external dependencies (MinIO, filesystem)
- [ ] Integration tests use real SQLite in-memory DB
- [ ] Async tests use `pytest-asyncio`
- [ ] Coverage >80% for business logic
- [ ] Fixtures properly clean up (rollback transactions)

### Code Quality Checklist

- [ ] Type hints on all function signatures
- [ ] Docstrings on public APIs
- [ ] No bare `except:` clauses
- [ ] Proper exception hierarchy (HTTPException for API errors)
- [ ] Configuration via Pydantic Settings, not globals
- [ ] No hardcoded paths (use `pathlib`)

### Common Pitfalls to Avoid

1. **SQLite write contention** - Use WAL mode or connection pooling
2. **Large file handling** - Use streaming, don't load full file in memory
3. **Async context leaks** - Always use `async with` for sessions
4. **Transaction boundaries** - Commit after all related operations
5. **Background task errors** - Errors in background tasks are silent, must log
6. **ZIP bomb protection** - Limit extracted file size from ZIPs
7. **Manifest versioning** - Handle both v1.0.0 (no `playback`) and v1.1.0

### Required Code Review Responses

When reviewing code from Codex AI, check these specific patterns:

```python
# GOOD - Path traversal protection
from bundle_tools.itts_common import is_safe_relative_path
if not is_safe_relative_path(path):
    raise ValueError("Unsafe path")

# BAD - No validation
zf.extract(path, output_dir)

# GOOD - Streaming file upload
async def read_in_chunks(file: UploadFile, chunk_size=8192):
    while chunk := await file.read(chunk_size):
        yield chunk

# BAD - Full file in memory
data = await file.read()  # Can OOM on large files

# GOOD - Async with proper cleanup
async with AsyncSessionLocal() as session:
    yield session

# BAD - Manual session management
session = AsyncSessionLocal()
# ... what if exception?
session.close()
```
