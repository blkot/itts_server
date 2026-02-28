# ITTS Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Docker-based backend for managing ITTS (IndexTTS Bundle) files with library management, custom audio export, concatenation, search, and backup/restore capabilities.

**Architecture:** FastAPI service with SQLite database and MinIO object storage. Two upload paths: (1) upload pre-built .itts files, (2) pack raw audio files into new .itts. Auto-playlists grouped by reference and emotion voices. Deduplication via SHA-256.

**Tech Stack:** FastAPI, SQLAlchemy, MinIO, Docker, pytest, uv

**Design Reference:** [docs/plans/2026-02-28-itts-backend-design.md](2026-02-28-itts-backend-design.md)
**Bundle Tools:** [bundle_tools/README.md](../../bundle_tools/README.md), [docs/BUNDLE_FORMAT.md](../../BUNDLE_FORMAT.md)

---

## Critical Implementation Notes

### For AI Implementer (Codex)

**READ THESE BEFORE STARTING:**

1. **Reuse existing code** - The `bundle_tools/` directory already has:
   - `itts_common.py` - Path validation, SHA-256 calculation, schema validation
   - `pack_itts.py` - ITTS packing logic
   - `unpack_itts.py` - ITTS unpacking logic

   **DO NOT reimplement these.** Import and reuse:
   ```python
   from bundle_tools.itts_common import (
       is_safe_relative_path,
       calculate_sha256,
       validate_manifest_with_schema,
   )
   ```

2. **Handle both manifest versions** - ITTS v1.0.0 is missing the `playback` field. Always check:
   ```python
   playback = manifest.get("playback")
   if not playback:
       # Handle v1.0.0 - no playback field
       playback = {"default_source": "combined", "fallback_order": ["combined"]}
   ```

3. **File size limits** - Add upload limits:
   ```python
   MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
   if file.size > MAX_UPLOAD_SIZE:
       raise HTTPException(status_code=413, detail="File too large")
   ```

4. **Stream large files** - Don't load full WAV in memory:
   ```python
   async def read_in_chunks(file: UploadFile, chunk_size=8192):
       while chunk := await file.read(chunk_size):
           yield chunk
   ```

5. **Path traversal protection** - Always validate:
   ```python
   from bundle_tools.itts_common import is_safe_relative_path
   if not is_safe_relative_path(untrusted_path):
       raise ValueError("Unsafe path")
   ```

6. **Async context managers** - Always use:
   ```python
   async with AsyncSessionLocal() as session:
       # work here
   # NEVER: session = AsyncSessionLocal(); ...; session.close()
   ```

7. **Transaction boundaries** - Commit after all related operations:
   ```python
   # GOOD - single transaction
   bundle = Bundle(...)
   session.add(bundle)
   playlist = Playlist(...)
   session.add(playlist)
   await session.commit()  # One commit

   # BAD - multiple commits, can leave inconsistent state
   await session.commit()  # Commit 1
   # ... more work ...
   await session.commit()  # Commit 2
   ```

8. **Background task errors** - Errors in FastAPI `BackgroundTasks` are silent! Must log:
   ```python
   @router.post("/export")
   async def create_export(..., background_tasks: BackgroundTasks):
       job_id = await create_job()
       background_tasks.add_task(process_with_logging, job_id)
       # Errors in process_with_logging won't appear in logs!
   ```

   Solution: Wrap in try/except and log explicitly.

9. **SQLite write concurrency** - Multiple writes can block. Use:
   ```python
   # In SQLAlchemy async engine setup
   engine = create_async_engine(
       "sqlite+aiosqlite:///...",
       connect_args={"check_same_thread": False}
   )
   ```

10. **MinIO client is synchronous** - The MinIO Python client is not async. Wrap properly:
    ```python
    from fastapi.concurrency import run_in_threadpool

    async def upload_file(...):
        await run_in_threadpool(
            sync_minio_client.put_object, ...
        )
    ```

### Code Review Checklist (Use After Each Phase)

See [design document Appendix](2026-02-28-itts-backend-design.md#appendix-code-review-guidelines) for complete checklist.

Brief version:
- [ ] Tests pass
- [ ] No hardcoded paths
- [ ] Proper error handling
- [ ] Type hints on functions
- [ ] SQL injection protected
- [ ] File uploads validated
- [ ] Async patterns correct
- [ ] **Commits are frequent and descriptive** (each step committed!)

**Git commit quality check:**
- [ ] Each step has its own commit
- [ ] Commit messages follow conventional commits format (feat:, fix:, test:, docs:)
- [ ] Phase summary commits include detailed body
- [ ] No "WIP" or "update" commits
- [ ] Each commit can be reverted independently

---

## Code Review Workflow

**How the review cycle works between you, Codex AI, and Claude (reviewer):**

### The Cycle

```
┌─────────────────┐
│   You ask Codex │
│   to implement  │
│   a step/phase  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Codex writes  │
│   code + tests  │
│   & commits     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Codex stops   │
│   and waits     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   You ask Claude│
│   to review     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Claude reviews│
│   & provides    │
│   feedback      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   You give      │
│   Claude's      │
│   feedback to   │
│   Codex         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Codex fixes   │
│   & commits     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Repeat review │
│   until APPROVED│
└─────────────────┘
```

### How to Request Review

**After Codex completes a step/phase:**

```bash
# 1. Check the commit
git log -1 --stat

# 2. Show me the changes
git diff HEAD~1 HEAD

# 3. Ask me to review
# Say: "Claude, please review the latest commit from Codex"
```

### Claude's Review Format

**My review will look like this:**

```
## Review: <commit message>

### Status: ✅ APPROVED / ⚠️ NEEDS FIXES

### What was changed:
- Added Bundle model with SHA-256 unique constraint
- Implemented check_duplicate() method
- Added unit tests

### Issues found:

#### 🔴 Critical (must fix before proceeding):
1. Missing foreign key cascade delete on Bundle.segments
   - Location: app/models/database.py:45
   - Fix: Add `ondelete="CASCADE"` to the ForeignKey

#### 🟡 Suggestions (recommended but not blocking):
1. Consider adding docstring to check_duplicate()
   - Not blocking, but would improve readability

### Security check:
- ✅ No hardcoded credentials
- ✅ Path traversal protected
- ⚠️ File size limit not implemented yet (add this in upload endpoint)

### Test coverage:
- ✅ Unit tests added
- ⚠️ Test for duplicate detection scenario missing

### Next steps:
1. Fix critical issues
2. Commit fixes
3. Request re-review
```

### How to Pass My Review to Codex

**Copy my review feedback and paste to Codex with this format:**

```
Claude reviewed your code and found issues that need fixing:

## Critical Issues (must fix):
1. Missing foreign key cascade delete on Bundle.segments
   Location: app/models/database.py:45
   Fix: Add `ondelete="CASCADE"` to the ForeignKey

Please fix these issues, commit the fixes, and stop for review again.
```

### Re-review Cycle

**After Codex makes fixes:**

```
┌─────────────────┐
│   Codex commits │
│   fixes         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   You ask Claude│
│   to RE-review   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Claude checks │
│   if fixes work │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
  Fixed    Still broken
    │         │
    ▼         ▼
 ✅ APPROVED  🔄 More fixes needed
    │         │
    ▼         ▼
 Next step  Repeat cycle
```

### Quick Review Commands

**When asking me to review, provide:**

```bash
# Option 1: Show the commit
git log -1 --patch

# Option 2: Show files changed
git show HEAD --stat

# Option 3: Show specific file
git show HEAD:app/models/database.py
```

### My Review Response Types

| Response | Meaning | What to do |
|----------|---------|------------|
| `✅ APPROVED` | No issues found | Proceed to next step |
| `⚠️ MINOR FIXES` | Small issues, clear how to fix | Fix quickly, re-review |
| `🔴 CRITICAL ISSUES` | Major problems, design concerns | Stop, discuss before fixing |
| `❌ REJECTED` | Wrong approach, needs redesign | Discuss and re-plan |

### Example Full Cycle

**You:** "Codex, implement Task 4: Create SQLAlchemy Models"

**Codex:** *Implements and commits* → "Done, stopped for review"

**You:** "Claude, please review Codex's latest commit" → *shows git log -1*

**Claude:** *Provides detailed review* → "Status: ⚠️ NEEDS FIXES - Missing cascade delete..."

**You:** *Pastes review to Codex* → "Claude found issues. Please fix: ..."

**Codex:** *Fixes and commits* → "Fixed, stopped for re-review"

**You:** "Claude, please re-review" → *shows git log -1*

**Claude:** "Status: ✅ APPROVED - All issues fixed"

**You:** "Codex, proceed to Task 5"

---

## Code Review Instructions

**For the AI Implementer (Codex):**
- Follow this plan task-by-task in order
- Write tests FIRST (TDD approach)
- Run tests after each task
- **COMMIT AFTER EACH STEP** (red, green, commit cycle)
- **COMMIT AFTER EACH PHASE** with descriptive phase summary
- Don't skip ahead - each task builds on previous

**Git Commit Pattern:**
```bash
# After each step within a task
git add <files-changed>
git commit -m "feat: <brief description of what this step does>"

# After completing a full task (all steps)
git add <task-files>
git commit -m "feat(task): complete <task name>"

# After completing a full phase
git add <phase-files>
git commit -m "feat(phase): complete <phase name>

- Implemented X service
- Added Y endpoint
- Added tests for Z
- All tests passing
"
```

**For the Code Reviewer:**
- Review after each phase (group of related tasks)
- Use the checklist in the design document (Appendix: Code Review Guidelines)
- Verify all phase gate criteria before proceeding
- Flag any security, performance, or quality issues immediately

**Phase Gate Review Points:**
1. After Phase 1 (Foundation) - Tasks 1-3
2. After Phase 2 (Models) - Tasks 4-5
3. After Phase 3 (Services) - Tasks 6-7
4. After Phase 4 (API) - Tasks 8-9
5. After Phase 5 (Export/Concat) - Tasks 10-13
6. After Phase 6 (Remaining) - Tasks 14-17
7. After Phase 7 (Testing) - Tasks 18-19
8. Final validation - Tasks 20-22

---

## Phase 1: Project Foundation

### Task 1: Initialize Python Project with uv

**Files:**
- Create: `pyproject.toml`
- Modify: `.gitignore`

**Step 1: Create pyproject.toml**

```bash
uv init --no-readme
```

**Step 2: Update pyproject.toml with dependencies**

Edit `pyproject.toml`:

```toml
[project]
name = "itts-backend"
version = "0.1.0"
description = "ITTS Bundle Management Backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy>=2.0.36",
    "aiosqlite>=0.20.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "minio>=7.2.8",
    "python-multipart>=0.0.17",
    "jsonschema>=4.23.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: Install dependencies**

```bash
uv sync
```

**Step 4: Update .gitignore**

Create `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# uv
.uv/
uv.lock

# Environment
.env
.venv
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Application data
data/
*.db
*.db-shm
*.db-wal
logs/
*.log

# Test coverage
.coverage
htmlcov/
.pytest_cache/
.bandit/

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
*.temp
/tmp/
```

**Step 5: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "chore: initialize project with uv and dependencies"
```

---

### Task 2: Create Application Structure

**Files:**
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `app/api/__init__.py`
- Create: `app/models/__init__.py`
- Create: `app/models/database.py`
- Create: `app/models/schemas.py`
- Create: `app/services/__init__.py`
- Create: `app/db/__init__.py`
- Create: `app/db/session.py`
- Create: `app/db/init_db.py`
- Create: `app/utils/__init__.py`
- Create: `app/utils/minio_client.py`

**Step 1: Create directory structure**

```bash
mkdir -p app/api app/models app/services app/db app/utils
touch app/__init__.py app/api/__init__.py app/models/__init__.py app/services/__init__.py app/db/__init__.py app/utils/__init__.py
```

**Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///data/db/itts.db"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "changeme"
    minio_bucket: str = "itts-bundles"
    minio_secure: bool = False

    # Backup
    backup_schedule: str = "0 2 * * *"
    backup_retention_days: int = 7

    # API
    api_title: str = "ITTS Backend API"
    api_version: str = "0.1.0"


settings = Settings()
```

**Step 3: Create db/session.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


async_engine = create_async_engine(
    settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

**Step 4: Create utils/minio_client.py**

```python
from minio import Minio

from app.config import settings


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


async def ensure_bucket_exists():
    client = get_minio_client()
    bucket_name = settings.minio_bucket
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
```

**Step 5: Create a minimal main.py**

```python
from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

**Step 6: Commit**

```bash
git add app/
git commit -m "feat: create application structure and configuration"
```

---

### Task 3: Docker Foundation

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.dockerignore`

**Step 1: Create .env.example**

```bash
# Database
DATABASE_URL=sqlite:///data/db/itts.db

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=changeme
MINIO_BUCKET=itts-bundles

# Backup
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=7
```

**Step 2: Create .dockerignore**

```dockerignore
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.uv
.venv
venv/
.env
data/
logs/
.git
.gitignore
.vscode
.idea
*.md
docs/
tests/
scripts/
```

**Step 3: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ ./app/
COPY bundle_tools/ ./bundle_tools/

# Create data directories
RUN mkdir -p /app/data/db /app/data/logs /app/data/backups

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 4: Create docker-compose.yml**

```yaml
services:
  itts-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
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

**Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example .dockerignore
git commit -m "feat: add Docker configuration"
```

---

### Phase 1 Gate Review

**Before proceeding to Phase 2, verify:**

- [ ] `docker-compose up -d` starts both services without errors
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] MinIO web UI accessible at http://localhost:9001
- [ ] `.gitignore` excludes `data/`, `.env`, `__pycache__`
- [ ] `pyproject.toml` includes: fastapi, sqlalchemy, aiosqlite, minio, pytest

**Security check:**
- [ ] `.env.example` doesn't contain real passwords
- [ ] `.gitignore` prevents committing `data/db/*.db`

---

## Phase 2: Database Models

### Task 4: Create SQLAlchemy Models

**Files:**
- Create: `app/models/database.py` (full implementation)
- Modify: `app/db/init_db.py`

**Step 1: Write failing test for models**

Create `tests/unit/test_models.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Bundle, Playlist, User


@pytest.mark.asyncio
async def test_create_bundle(db_session: AsyncSession):
    bundle = Bundle(
        title="Test Bundle",
        filename="test.itts",
        s3_key="bundles/test.itts",
        manifest_json='{"format": "index-tts-bundle"}',
        generated_audio_sha256="abc123",
        reference_voice="voice1",
        emotion_voice="happy",
        mode="combined",
        total_duration_ms=5000,
    )
    db_session.add(bundle)
    await db_session.commit()
    await db_session.refresh(bundle)

    assert bundle.id is not None
    assert bundle.title == "Test Bundle"


@pytest.mark.asyncio
async def test_create_auto_playlist(db_session: AsyncSession):
    playlist = Playlist(
        name="voice1",
        is_auto_generated=True,
        auto_type="reference",
        auto_value="voice1",
    )
    db_session.add(playlist)
    await db_session.commit()
    await db_session.refresh(playlist)

    assert playlist.id is not None
    assert playlist.auto_type == "reference"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: FAIL with "Bundle does not exist"

**Step 3: Implement database models**

Create `app/models/database.py`:

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(String, default=datetime.utcnow)


class Bundle(Base):
    __tablename__ = "bundles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    s3_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Deduplication
    generated_audio_sha256: Mapped[Optional[str]] = mapped_column(String, unique=True)

    # Auto-playlist grouping
    reference_voice: Mapped[Optional[str]] = mapped_column(String)
    emotion_voice: Mapped[Optional[str]] = mapped_column(String)

    mode: Mapped[Optional[str]] = mapped_column(String)
    total_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Concatenation
    is_concatenated: Mapped[bool] = mapped_column(Boolean, default=False)
    source_bundle_ids: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(String, default=datetime.utcnow)

    # Relationships
    segments: Mapped[list["Segment"]] = relationship(
        "Segment", back_populates="bundle", cascade="all, delete-orphan"
    )


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[Optional[str]] = mapped_column(Text)
    start_ms: Mapped[Optional[int]] = mapped_column(Integer)
    end_ms: Mapped[Optional[int]] = mapped_column(Integer)
    filename: Mapped[Optional[str]] = mapped_column(String)
    sha256: Mapped[Optional[str]] = mapped_column(String)

    # Relationship
    bundle: Mapped["Bundle"] = relationship("Bundle", back_populates="segments")

    __table_args__ = (UniqueConstraint("bundle_id", "segment_index", name="uq_bundle_segment"),)


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_type: Mapped[Optional[str]] = mapped_column(String)  # 'reference' or 'emotion'
    auto_value: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(String, default=datetime.utcnow)


class PlaylistEntry(Base):
    __tablename__ = "playlist_entries"

    playlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True
    )
    bundle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bundles.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(String, default=datetime.utcnow)


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False
    )
    s3_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    segment_indices: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    join_silence_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(String, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # 'export' or 'concat'
    status: Mapped[str] = mapped_column(String, nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    input_params: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    result_bundle_id: Mapped[Optional[int]] = mapped_column(Integer)
    result_export_id: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(String, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(String)
```

**Step 4: Create database initialization**

Create `app/db/init_db.py`:

```python
from sqlalchemy import select
from app.db.session import async_engine
from app.db.session import Base
from app.models.database import Playlist


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create main playlist
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Playlist).where(Playlist.name == "Main"))
        if not result.scalar_one_or_none():
            main_playlist = Playlist(
                name="Main",
                is_auto_generated=False,
            )
            session.add(main_playlist)
            await session.commit()
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add app/models/database.py app/db/init_db.py tests/unit/test_models.py
git commit -m "feat: add SQLAlchemy models for bundles, playlists, exports, jobs"
```

---

### Task 5: Create Pydantic Schemas

**Files:**
- Create: `app/models/schemas.py`

**Step 1: Write failing test**

Create `tests/unit/test_schemas.py`:

```python
import pytest
from app.models.schemas import BundleCreate, BundleResponse, BundleListResponse


def test_bundle_response_schema():
    data = {
        "id": 1,
        "title": "Test",
        "filename": "test.itts",
        "s3_key": "bundles/test.itts",
        "reference_voice": "voice1",
        "emotion_voice": "happy",
        "mode": "combined",
        "is_concatenated": False,
        "created_at": "2026-02-28T00:00:00Z",
    }
    bundle = BundleResponse(**data)
    assert bundle.id == 1
    assert bundle.title == "Test"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_schemas.py -v
```

Expected: FAIL with "BundleResponse does not exist"

**Step 3: Implement schemas**

Create `app/models/schemas.py`:

```python
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class BundleResponse(BaseModel):
    id: int
    title: str
    filename: str
    s3_key: str
    reference_voice: Optional[str] = None
    emotion_voice: Optional[str] = None
    mode: Optional[str] = None
    total_duration_ms: Optional[int] = None
    is_concatenated: bool = False
    created_at: str

    class Config:
        from_attributes = True


class BundleListResponse(BaseModel):
    total: int
    items: List[BundleResponse]
    page: int
    page_size: int


class SegmentResponse(BaseModel):
    id: int
    segment_index: int
    text_prompt: str
    normalized_text: Optional[str] = None
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None

    class Config:
        from_attributes = True


class ExportRequest(BaseModel):
    bundle_id: int
    segment_indices: List[int]
    silence_ms: int = Field(default=100, ge=0, le=5000)


class JobResponse(BaseModel):
    id: int
    type: str
    status: str
    progress: float
    result_bundle_id: Optional[int] = None
    result_export_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class PlaylistResponse(BaseModel):
    id: int
    name: str
    is_auto_generated: bool
    auto_type: Optional[str] = None
    auto_value: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class PackRequest(BaseModel):
    title: str
    prompt_text: str
    reference_title: str
    emotion_title: str


class DuplicateResponse(BaseModel):
    status: str = "duplicate"
    message: str
    existing_bundle: BundleResponse
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_schemas.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/models/schemas.py tests/unit/test_schemas.py
git commit -m "feat: add Pydantic schemas for API requests/responses"
```

---

### Phase 2 Gate Review

**Before proceeding to Phase 3, verify:**

- [ ] All models have proper type hints
- [ ] Foreign key relationships have `ondelete="CASCADE"`
- [ ] `Bundle.generated_audio_sha256` has `unique=True`
- [ ] `PlaylistEntry` has composite primary key
- [ ] Unit tests pass: `uv run pytest tests/unit/test_models.py tests/unit/test_schemas.py -v`

**Data integrity check:**
- [ ] Deleting a bundle cascades to its segments
- [ ] Deleting a playlist cascades to its entries
- [ ] Duplicate SHA-256 constraint enforced

**Important: Reuse bundle_tools for validation**

When implementing ITTS file handling, always use:
```python
from bundle_tools.itts_common import (
    is_safe_relative_path,
    calculate_sha256,
    validate_manifest_with_schema,
)
```

Don't reimplement - reuse existing validated code!

---

## Phase 3: Core Services

### Task 6: Storage Service

**Files:**
- Create: `app/services/storage_service.py`
- Create: `tests/unit/test_storage_service.py`

**Step 1: Write failing test**

Create `tests/unit/test_storage_service.py`:

```python
import pytest
from unittest.mock import Mock, patch
from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_upload_file():
    mock_minio = Mock()
    with patch("app.services.storage_service.get_minio_client", return_value=mock_minio):
        service = StorageService()
        await service.upload_file("test.itts", b"fake data", "bundles/")

        mock_minio.put_object.assert_called_once()
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_storage_service.py -v
```

Expected: FAIL with "StorageService does not exist"

**Step 3: Implement storage service**

Create `app/services/storage_service.py`:

```python
import io
from typing import BinaryIO
from minio import Minio

from app.utils.minio_client import get_minio_client
from app.config import settings


class StorageService:
    def __init__(self):
        self.client: Minio = get_minio_client()
        self.bucket = settings.minio_bucket

    async def upload_file(self, filename: str, data: bytes, prefix: str = "") -> str:
        """Upload file to MinIO and return S3 key"""
        s3_key = f"{prefix}/{filename}" if prefix else filename
        self.client.put_object(
            self.bucket,
            s3_key,
            io.BytesIO(data),
            length=len(data),
        )
        return s3_key

    async def download_file(self, s3_key: str) -> bytes:
        """Download file from MinIO"""
        response = self.client.get_object(self.bucket, s3_key)
        return response.read()

    async def delete_file(self, s3_key: str) -> None:
        """Delete file from MinIO"""
        self.client.remove_object(self.bucket, s3_key)

    async def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self.client.stat_object(self.bucket, s3_key)
            return True
        except Exception:
            return False
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_storage_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/storage_service.py tests/unit/test_storage_service.py
git commit -m "feat: add MinIO storage service"
```

---

### Task 7: Bundle Service

**Files:**
- Create: `app/services/bundle_service.py`
- Create: `tests/unit/test_bundle_service.py`

**Step 1: Write failing test**

Create `tests/unit/test_bundle_service.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.bundle_service import BundleService
from app.models.database import Bundle


@pytest.mark.asyncio
async def test_check_duplicate_found():
    mock_db = Mock(spec=AsyncSession)
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = Bundle(id=1, title="Existing")
    mock_db.execute.return_value = mock_result

    service = BundleService(mock_db)
    duplicate = await service.check_duplicate("abc123")

    assert duplicate is not None
    assert duplicate.id == 1
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_bundle_service.py::test_check_duplicate_found -v
```

Expected: FAIL with "BundleService does not exist"

**Step 3: Implement bundle service**

Create `app/services/bundle_service.py`:

```python
import json
import zipfile
import io
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Bundle, Segment, Playlist, PlaylistEntry
from app.models.schemas import BundleResponse, SegmentResponse


class BundleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_duplicate(self, sha256: str) -> Optional[Bundle]:
        """Check if bundle with same SHA-256 exists"""
        result = await self.db.execute(
            select(Bundle).where(Bundle.generated_audio_sha256 == sha256)
        )
        return result.scalar_one_or_none()

    async def create_bundle(
        self,
        title: str,
        filename: str,
        s3_key: str,
        manifest_json: str,
        generated_audio_sha256: Optional[str] = None,
        reference_voice: Optional[str] = None,
        emotion_voice: Optional[str] = None,
        mode: Optional[str] = None,
        total_duration_ms: Optional[int] = None,
    ) -> BundleResponse:
        """Create a new bundle and auto-playlists"""
        bundle = Bundle(
            title=title,
            filename=filename,
            s3_key=s3_key,
            manifest_json=manifest_json,
            generated_audio_sha256=generated_audio_sha256,
            reference_voice=reference_voice,
            emotion_voice=emotion_voice,
            mode=mode,
            total_duration_ms=total_duration_ms,
        )
        self.db.add(bundle)
        await self.db.flush()

        # Create auto-playlists
        await self._create_auto_playlists(bundle)

        # Add to main playlist
        await self._add_to_main_playlist(bundle.id)

        await self.db.commit()
        await self.db.refresh(bundle)

        return BundleResponse.model_validate(bundle)

    async def _create_auto_playlists(self, bundle: Bundle) -> None:
        """Create auto-playlists for reference and emotion"""
        if bundle.reference_voice:
            await self._get_or_create_playlist(
                bundle.reference_voice, "reference", bundle.reference_voice
            )
            await self._add_to_playlist(bundle.id, bundle.reference_voice)

        if bundle.emotion_voice:
            await self._get_or_create_playlist(
                bundle.emotion_voice, "emotion", bundle.emotion_voice
            )
            await self._add_to_playlist(bundle.id, bundle.emotion_voice)

    async def _get_or_create_playlist(
        self, name: str, auto_type: str, auto_value: str
    ) -> Playlist:
        """Get existing playlist or create new auto-playlist"""
        result = await self.db.execute(select(Playlist).where(Playlist.name == name))
        playlist = result.scalar_one_or_none()

        if not playlist:
            playlist = Playlist(
                name=name,
                is_auto_generated=True,
                auto_type=auto_type,
                auto_value=auto_value,
            )
            self.db.add(playlist)
            await self.db.flush()

        return playlist

    async def _add_to_playlist(self, bundle_id: int, playlist_name: str) -> None:
        """Add bundle to playlist"""
        result = await self.db.execute(
            select(Playlist).where(Playlist.name == playlist_name)
        )
        playlist = result.scalar_one_or_none()

        if playlist:
            entry = PlaylistEntry(playlist_id=playlist.id, bundle_id=bundle_id)
            self.db.add(entry)

    async def _add_to_main_playlist(self, bundle_id: int) -> None:
        """Add bundle to main playlist"""
        await self._add_to_playlist(bundle_id, "Main")

    async def get_bundle(self, bundle_id: int) -> Optional[BundleResponse]:
        """Get bundle by ID"""
        bundle = await self.db.get(Bundle, bundle_id)
        if not bundle:
            return None
        return BundleResponse.model_validate(bundle)

    async def list_bundles(
        self, page: int = 1, page_size: int = 50
    ) -> List[BundleResponse]:
        """List all bundles with pagination"""
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Bundle).order_by(Bundle.created_at.desc()).offset(offset).limit(page_size)
        )
        bundles = result.scalars().all()
        return [BundleResponse.model_validate(b) for b in bundles]

    async def delete_bundle(self, bundle_id: int) -> bool:
        """Delete bundle by ID"""
        bundle = await self.db.get(Bundle, bundle_id)
        if not bundle:
            return False

        await self.db.delete(bundle)
        await self.db.commit()
        return True

    async def get_segments(self, bundle_id: int) -> List[SegmentResponse]:
        """Get all segments for a bundle"""
        result = await self.db.execute(
            select(Segment)
            .where(Segment.bundle_id == bundle_id)
            .order_by(Segment.segment_index)
        )
        segments = result.scalars().all()
        return [SegmentResponse.model_validate(s) for s in segments]

    @staticmethod
    def extract_manifest_from_itts(itts_data: bytes) -> dict:
        """Extract and parse manifest from ITTS file"""
        with zipfile.ZipFile(io.BytesIO(itts_data)) as zf:
            manifest_json = zf.read("manifest.json").decode("utf-8")
            return json.loads(manifest_json)

    @staticmethod
    def extract_file_from_itts(itts_data: bytes, path: str) -> bytes:
        """Extract a specific file from ITTS"""
        with zipfile.ZipFile(io.BytesIO(itts_data)) as zf:
            return zf.read(path)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_bundle_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/bundle_service.py tests/unit/test_bundle_service.py
git commit -m "feat: add bundle service with CRUD and auto-playlists"
```

---

## Phase 4: API Endpoints

### Task 8: Bundle Upload Endpoint

**Files:**
- Create: `app/api/bundles.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_upload_workflow.py`

**Step 1: Write failing test**

Create `tests/integration/test_upload_workflow.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_upload_itts_success(test_db_session, mock_minio):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
            response = await client.post(
                "/api/bundles",
                files={"file": ("test.itts", f, "application/octet-stream")}
            )

        assert response.status_code == 201
        data = response.json()
        assert "bundle_id" in data
        assert data["reference_voice"] == "[wls]现在微商叫轻资产创业招募..."
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_upload_workflow.py -v
```

Expected: FAIL with "404 Not Found"

**Step 3: Implement bundle upload endpoint**

Create `app/api/bundles.py`:

```python
import io
import zipfile
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.bundle_service import BundleService
from app.services.storage_service import StorageService
from app.models.schemas import BundleResponse, BundleListResponse, DuplicateResponse, SegmentResponse
from app.utils.minio_client import ensure_bucket_exists

router = APIRouter(prefix="/api/bundles", tags=["bundles"])

# Ensure MinIO bucket exists on startup
@router.on_event("startup")
async def startup():
    await ensure_bucket_exists()


@router.post("", response_model=BundleResponse, status_code=status.HTTP_201_CREATED)
async def upload_bundle(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an existing .itts file"""
    # Read file data
    itts_data = await file.read()

    # Extract manifest
    manifest = BundleService.extract_manifest_from_itts(itts_data)

    # Get SHA-256 for deduplication
    sha256 = None
    if "generated_audio" in manifest:
        generated = manifest["generated_audio"]
        if generated.get("mode") == "combined" and "combined" in generated:
            sha256 = generated["combined"].get("sha256")

    # Check for duplicate
    if sha256:
        bundle_service = BundleService(db)
        duplicate = await bundle_service.check_duplicate(sha256)
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "duplicate",
                    "message": "This ITTS already exists in your library",
                    "existing_bundle": BundleResponse.model_validate(duplicate).model_dump(),
                },
            )

    # Upload to MinIO
    storage = StorageService()
    s3_key = await storage.upload_file(file.filename, itts_data, "bundles")

    # Create bundle record
    bundle_service = BundleService(db)
    response = await bundle_service.create_bundle(
        title=manifest.get("bundle_id", file.filename),
        filename=file.filename,
        s3_key=s3_key,
        manifest_json=manifest,
        generated_audio_sha256=sha256,
        reference_voice=manifest.get("reference_audio", {}).get("title"),
        emotion_voice=manifest.get("emotion_audio", {}).get("title"),
        mode=manifest.get("generated_audio", {}).get("mode"),
    )

    return response


@router.get("", response_model=BundleListResponse)
async def list_bundles(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all bundles"""
    service = BundleService(db)
    items = await service.list_bundles(page, page_size)

    # Get total count
    from sqlalchemy import func, select
    from app.models.database import Bundle
    result = await db.execute(select(func.count()).select_from(Bundle))
    total = result.scalar()

    return BundleListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size,
    )


@router.get("/{bundle_id}", response_model=BundleResponse)
async def get_bundle(
    bundle_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get bundle by ID"""
    service = BundleService(db)
    bundle = await service.get_bundle(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@router.get("/{bundle_id}/segments", response_model=list[SegmentResponse])
async def get_bundle_segments(
    bundle_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all segments for a bundle"""
    service = BundleService(db)
    return await service.get_segments(bundle_id)


@router.delete("/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bundle(
    bundle_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a bundle"""
    service = BundleService(db)
    success = await service.delete_bundle(bundle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return None
```

**Step 4: Register router in main.py**

Update `app/main.py`:

```python
from fastapi import FastAPI
from app.config import settings
from app.api.bundles import router as bundles_router

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

app.include_router(bundles_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

**Step 5: Add test fixtures**

Create `tests/conftest.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock

from app.db.session import Base, get_db
from app.models.database import Bundle


@pytest.fixture(scope="function")
async def test_db_session():
    """Create a test database session"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture
def mock_minio():
    """Mock MinIO client"""
    from unittest.mock import Mock
    mock = Mock()
    mock.put_object = Mock()
    mock.get_object = Mock(return_value=Mock(read=lambda: b"fake data"))
    mock.remove_object = Mock()
    mock.stat_object = Mock()
    mock.bucket_exists = Mock(return_value=True)
    mock.make_bucket = Mock()

    import app.services.storage_service
    original = app.services.storage_service.get_minio_client
    app.services.storage_service.get_minio_client = lambda: mock

    yield mock

    app.services.storage_service.get_minio_client = original


@pytest.fixture
async def db_session(test_db_session):
    """Override get_db dependency"""
    async def override_get_db():
        yield test_db_session

    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    yield test_db_session
    app.dependency_overrides.clear()
```

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/integration/test_upload_workflow.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add app/api/bundles.py app/main.py tests/conftest.py tests/integration/test_upload_workflow.py
git commit -m "feat: add bundle upload endpoint with deduplication"
```

---

### Task 9: Pack Endpoint

**Files:**
- Modify: `app/services/pack_service.py` (create)
- Modify: `app/api/bundles.py`

**Step 1: Write failing test**

Create `tests/integration/test_pack_workflow.py`:

```python
import pytest
import zipfile
import io
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_pack_from_raw_files(test_db_session, mock_minio):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Read test ITTS to extract files
        with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
            itts_data = f.read()

        # Extract files for testing
        with zipfile.ZipFile(io.BytesIO(itts_data)) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            combined = zf.read("audio/generated/combined.wav")
            reference = zf.read("audio/reference.wav")
            emotion = zf.read("audio/emotion.wav")

        response = await client.post(
            "/api/bundles/pack",
            data={
                "title": "Test Pack",
                "prompt_text": manifest["prompt"]["text"],
                "reference_title": manifest["reference_audio"]["title"],
                "emotion_title": manifest["emotion_audio"]["title"],
            },
            files={
                "generated_combined": ("combined.wav", io.BytesIO(combined), "audio/wav"),
                "reference_audio": ("reference.wav", io.BytesIO(reference), "audio/wav"),
                "emotion_audio": ("emotion.wav", io.BytesIO(emotion), "audio/wav"),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "bundle_id" in data
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_pack_workflow.py -v
```

Expected: FAIL with "404 Not Found"

**Step 3: Implement pack service**

Create `app/services/pack_service.py`:

```python
import io
import json
import zipfile
import hashlib
from datetime import datetime
from typing import Dict, Any

from app.services.bundle_service import BundleService
from app.services.storage_service import StorageService


class PackService:
    def __init__(self, bundle_service: BundleService, storage: StorageService):
        self.bundle_service = bundle_service
        self.storage = storage

    async def pack_from_raw_files(
        self,
        title: str,
        prompt_text: str,
        reference_title: str,
        emotion_title: str,
        generated_combined: bytes,
        reference_audio: bytes,
        emotion_audio: bytes,
    ) -> Dict[str, Any]:
        """Pack raw audio files into ITTS bundle"""

        # Calculate SHA-256 for deduplication
        generated_sha256 = hashlib.sha256(generated_combined).hexdigest()

        # Check for duplicate
        duplicate = await self.bundle_service.check_duplicate(generated_sha256)
        if duplicate:
            return {"status": "duplicate", "existing_bundle": duplicate}

        # Create ITTS manifest
        manifest = self._create_manifest(
            title=title,
            prompt_text=prompt_text,
            reference_title=reference_title,
            emotion_title=emotion_title,
            generated_combined_sha256=generated_sha256,
            generated_bytes=len(generated_combined),
            reference_bytes=len(reference_audio),
            emotion_bytes=len(emotion_audio),
        )

        # Create ZIP file in memory
        itts_buffer = io.BytesIO()
        with zipfile.ZipFile(itts_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Add audio files
            zf.writestr("audio/generated/combined.wav", generated_combined)
            zf.writestr("audio/reference.wav", reference_audio)
            zf.writestr("audio/emotion.wav", emotion_audio)

        itts_data = itts_buffer.getvalue()

        # Generate filename
        filename = f"{title.replace(' ', '_')}.itts"
        s3_key = await self.storage.upload_file(filename, itts_data, "bundles")

        # Create bundle record
        response = await self.bundle_service.create_bundle(
            title=title,
            filename=filename,
            s3_key=s3_key,
            manifest_json=json.dumps(manifest),
            generated_audio_sha256=generated_sha256,
            reference_voice=reference_title,
            emotion_voice=emotion_title,
            mode="combined",
        )

        return {"status": "created", "bundle": response}

    def _create_manifest(
        self,
        title: str,
        prompt_text: str,
        reference_title: str,
        emotion_title: str,
        generated_combined_sha256: str,
        generated_bytes: int,
        reference_bytes: int,
        emotion_bytes: int,
    ) -> Dict[str, Any]:
        """Create ITTS manifest JSON"""
        return {
            "format": "index-tts-bundle",
            "version": "1.0.0",
            "bundle_id": title,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "prompt": {"text": prompt_text},
            "playback": {
                "default_source": "combined",
                "fallback_order": ["combined"],
                "segment_order": "index_asc",
            },
            "generated_audio": {
                "mode": "combined",
                "combined": {
                    "path": "audio/generated/combined.wav",
                    "mime_type": "audio/wav",
                    "sha256": generated_combined_sha256,
                    "bytes": generated_bytes,
                },
            },
            "reference_audio": {
                "path": "audio/reference.wav",
                "mime_type": "audio/wav",
                "title": reference_title,
                "bytes": reference_bytes,
            },
            "emotion_audio": {
                "path": "audio/emotion.wav",
                "mime_type": "audio/wav",
                "title": emotion_title,
                "bytes": emotion_bytes,
            },
            "generator": {
                "app": "ITTS Backend",
                "model": "unknown",
            },
        }
```

**Step 4: Add pack endpoint to bundles.py**

Add to `app/api/bundles.py`:

```python
import json
from fastapi import UploadFile, File
from app.models.schemas import PackRequest
from app.services.pack_service import PackService


@router.post("/pack", response_model=BundleResponse, status_code=status.HTTP_201_CREATED)
async def pack_bundle(
    title: str = Form(...),
    prompt_text: str = Form(...),
    reference_title: str = Form(...),
    emotion_title: str = Form(...),
    generated_combined: UploadFile = File(...),
    reference_audio: UploadFile = File(...),
    emotion_audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Pack raw audio files into a new ITTS bundle"""
    # Read uploaded files
    generated_data = await generated_combined.read()
    reference_data = await reference_audio.read()
    emotion_data = await emotion_audio.read()

    # Pack into ITTS
    bundle_service = BundleService(db)
    storage = StorageService()
    pack_service = PackService(bundle_service, storage)

    result = await pack_service.pack_from_raw_files(
        title=title,
        prompt_text=prompt_text,
        reference_title=reference_title,
        emotion_title=emotion_title,
        generated_combined=generated_data,
        reference_audio=reference_data,
        emotion_audio=emotion_data,
    )

    if result["status"] == "duplicate":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "duplicate",
                "message": "This ITTS already exists in your library",
                "existing_bundle": result["existing_bundle"],
            },
        )

    return result["bundle"]
```

Also add to imports:
```python
from fastapi import Form
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/integration/test_pack_workflow.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add app/services/pack_service.py tests/integration/test_pack_workflow.py
git commit -m "feat: add pack endpoint for creating ITTS from raw files"
```

---

## Phase 5: Export & Concatenation

### Task 10: Export Service

**Files:**
- Create: `app/services/export_service.py`
- Create: `tests/unit/test_export_service.py`

**Step 1: Write failing test**

Create `tests/unit/test_export_service.py`:

```python
import pytest
import io
import wave
from unittest.mock import Mock, AsyncMock, patch
from app.services.export_service import ExportService


@pytest.mark.asyncio
async def test_join_segments():
    # Create mock WAV data (1 second of silence)
    sample_rate = 22050
    duration = 1
    mock_wav = io.BytesIO()
    with wave.open(mock_wav, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * sample_rate * duration)

    mock_db = Mock()
    mock_storage = Mock()
    mock_storage.download_file = AsyncMock(return_value=mock_wav.getvalue())

    service = ExportService(mock_db, mock_storage)

    # Mock segments
    mock_segments = [
        Mock(s3_key="seg0.wav", start_ms=0, end_ms=1000),
        Mock(s3_key="seg1.wav", start_ms=1000, end_ms=2000),
    ]

    result = await service.join_segments(mock_segments, silence_ms=100)

    assert result is not None
    assert len(result) > 0
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_export_service.py -v
```

Expected: FAIL with "ExportService does not exist"

**Step 3: Implement export service**

Create `app/services/export_service.py`:

```python
import io
import wave
import struct
import json
from typing import List, Optional
from fastapi import BackgroundTasks

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import Bundle, Segment, Export, Job
from app.services.storage_service import StorageService
from app.services.bundle_service import BundleService


class ExportService:
    def __init__(self, db: AsyncSession, storage: StorageService):
        self.db = db
        self.storage = storage
        self.bundle_service = BundleService(db)

    async def create_export_job(
        self, bundle_id: int, segment_indices: List[int], silence_ms: int = 100
    ) -> int:
        """Create an async job for segment export"""
        job = Job(
            type="export",
            status="pending",
            input_params=json.dumps({
                "bundle_id": bundle_id,
                "segment_indices": segment_indices,
                "silence_ms": silence_ms,
            }),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return job.id

    async def process_export_job(self, job_id: int) -> Optional[int]:
        """Process export job and return export_id"""
        job = await self.db.get(Job, job_id)
        if not job:
            return None

        try:
            job.status = "processing"
            await self.db.commit()

            params = json.loads(job.input_params)
            bundle_id = params["bundle_id"]
            segment_indices = params["segment_indices"]
            silence_ms = params.get("silence_ms", 100)

            # Get bundle from MinIO
            bundle = await self.db.get(Bundle, bundle_id)
            if not bundle:
                raise ValueError("Bundle not found")

            # Extract segments from ITTS
            itts_data = await self.storage.download_file(bundle.s3_key)
            segments_data = self._extract_segments_from_itts(itts_data, segment_indices)

            # Join segments
            joined_audio = await self.join_segments(
                segments_data, silence_ms=silence_ms
            )

            # Upload export to MinIO
            export_filename = f"export_{bundle_id}_{job_id}.wav"
            s3_key = await self.storage.upload_file(export_filename, joined_audio, "exports")

            # Create export record
            export = Export(
                bundle_id=bundle_id,
                s3_key=s3_key,
                segment_indices=json.dumps(segment_indices),
                join_silence_ms=silence_ms,
            )
            self.db.add(export)
            await self.db.commit()
            await self.db.refresh(export)

            # Update job
            job.status = "completed"
            job.result_export_id = export.id
            job.progress = 1.0
            await self.db.commit()

            return export.id

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()
            raise

    async def join_segments(
        self, segments: List[tuple], silence_ms: int = 100
    ) -> bytes:
        """Join WAV segments with optional silence"""
        if not segments:
            raise ValueError("No segments to join")

        # Read first segment to get format
        first_data, first_start, first_end = segments[0]
        first_wav = wave.open(io.BytesIO(first_data), "rb")
        sample_rate = first_wav.getframerate()
        channels = first_wav.getnchannels()
        sampwidth = first_wav.getsampwidth()
        first_wav.close()

        # Calculate silence samples
        silence_samples = int((silence_ms / 1000) * sample_rate)
        silence_frame = b"\x00\x00" * silence_samples * channels

        # Join all segments
        output = io.BytesIO()
        with wave.open(output, "wb") as out_wav:
            out_wav.setnchannels(channels)
            out_wav.setsampwidth(sampwidth)
            out_wav.setframerate(sample_rate)

            for i, (data, start_ms, end_ms) in enumerate(segments):
                # Write segment
                wav = wave.open(io.BytesIO(data), "rb")
                out_wav.writeframes(wav.readframes(wav.getnframes()))
                wav.close()

                # Add silence between segments
                if i < len(segments) - 1:
                    out_wav.writeframes(silence_frame)

        return output.getvalue()

    def _extract_segments_from_itts(
        self, itts_data: bytes, segment_indices: List[int]
    ) -> List[tuple]:
        """Extract specific segments from ITTS file"""
        import zipfile
        from app.services.bundle_service import BundleService

        manifest = BundleService.extract_manifest_from_itts(itts_data)
        generated = manifest.get("generated_audio", {})

        segments = []

        if generated.get("mode") == "combined" and "segments" in manifest.get("prompt", {}):
            # Extract from combined using segment timing
            combined_path = generated["combined"]["path"]
            combined_data = BundleService.extract_file_from_itts(itts_data, combined_path)

            prompt_segments = manifest["prompt"].get("segments", [])

            for idx in segment_indices:
                if idx >= len(prompt_segments):
                    continue

                seg = prompt_segments[idx]
                start_ms = seg.get("start_ms", 0)
                end_ms = seg.get("end_ms")

                # Extract segment from combined WAV
                segment_data = self._extract_wav_segment(
                    combined_data, start_ms, end_ms
                )
                segments.append((segment_data, start_ms, end_ms))

        elif generated.get("mode") in ("segments", "both"):
            # Extract individual segment files
            segment_files = generated.get("segments", [])

            for seg_file in segment_files:
                if seg_file["index"] in segment_indices:
                    path = seg_file["path"]
                    data = BundleService.extract_file_from_itts(itts_data, path)
                    segments.append((
                        data,
                        seg_file.get("start_ms", 0),
                        seg_file.get("end_ms"),
                    ))

        return segments

    def _extract_wav_segment(self, wav_data: bytes, start_ms: int, end_ms: int) -> bytes:
        """Extract a segment from a WAV file by millisecond range"""
        wav = wave.open(io.BytesIO(wav_data), "rb")
        sample_rate = wav.getframerate()
        sampwidth = wav.getsampwidth()
        channels = wav.getnchannels()

        start_frame = int((start_ms / 1000) * sample_rate)
        end_frame = int((end_ms / 1000) * sample_rate)

        wav.setpos(start_frame)
        frames = wav.readframes(end_frame - start_frame)
        wav.close()

        return frames
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_export_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/export_service.py tests/unit/test_export_service.py
git commit -m "feat: add export service for joining segments"
```

---

### Task 11: Export API Endpoint

**Files:**
- Create: `app/api/export.py`
- Modify: `app/main.py`

**Step 1: Write failing test**

Create `tests/integration/test_export_workflow.py`:

```python
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_export_workflow(test_db_session, mock_minio):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First upload a bundle
        with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
            upload = await client.post(
                "/api/bundles",
                files={"file": ("test.itts", f, "application/octet-stream")}
            )
        bundle_id = upload.json()["id"]

        # Create export
        export = await client.post(
            "/api/export",
            json={
                "bundle_id": bundle_id,
                "segment_indices": [0],
                "silence_ms": 100,
            },
        )
        assert export.status_code == 201
        job_id = export.json()["job_id"]

        # Poll for completion
        for _ in range(10):
            status = await client.get(f"/api/jobs/{job_id}")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("Export job did not complete")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_export_workflow.py -v
```

Expected: FAIL with "404 Not Found"

**Step 3: Implement export endpoint**

Create `app/api/export.py`:

```python
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.export_service import ExportService
from app.services.storage_service import StorageService
from app.models.schemas import JobResponse
from app.models.database import Job, Export

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/export", status_code=status.HTTP_201_CREATED)
async def create_export(
    request: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a segment export job"""
    bundle_id = request.get("bundle_id")
    segment_indices = request.get("segment_indices", [])
    silence_ms = request.get("silence_ms", 100)

    storage = StorageService()
    service = ExportService(db, storage)

    job_id = await service.create_export_job(bundle_id, segment_indices, silence_ms)

    # Process in background
    background_tasks.add_task(service.process_export_job, job_id)

    return {"job_id": job_id}


@router.get("/export/{export_id}")
async def download_export(
    export_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Download exported WAV file"""
    export = await db.get(Export, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    storage = StorageService()
    data = await storage.download_file(export.s3_key)

    return StreamingResponse(
        io.BytesIO(data),
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="export_{export_id}.wav"',
        },
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get job status"""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)
```

**Step 4: Register router in main.py**

Update `app/main.py`:

```python
from fastapi import FastAPI
from app.config import settings
from app.api.bundles import router as bundles_router
from app.api.export import router as export_router

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

app.include_router(bundles_router)
app.include_router(export_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/integration/test_export_workflow.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add app/api/export.py app/main.py tests/integration/test_export_workflow.py
git commit -m "feat: add export endpoint with async job processing"
```

---

### Task 12: Concatenation Service

**Files:**
- Create: `app/services/concat_service.py`
- Create: `tests/unit/test_concat_service.py`

**Step 1: Write failing test**

Create `tests/unit/test_concat_service.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.concat_service import ConcatService


@pytest.mark.asyncio
async def test_create_concat_bundle():
    mock_db = Mock()
    mock_storage = Mock()

    service = ConcatService(mock_db, mock_storage)

    # Mock source bundles
    mock_bundles = [
        Mock(s3_key="bundle1.itts", manifest_json='{"prompt": {"text": "Hello"}}'),
        Mock(s3_key="bundle2.itts", manifest_json='{"prompt": {"text": "World"}}'),
    ]

    result = await service.create_concat_bundles(
        title="Concat Test",
        items=[{"bundle_id": 1, "segments": [0]}, {"bundle_id": 2, "segments": [0]}],
        silence_ms=100,
    )

    assert result is not None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_concat_service.py -v
```

Expected: FAIL with "ConcatService does not exist"

**Step 3: Implement concat service**

Create `app/services/concat_service.py`:

```python
import json
import io
import zipfile
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import Bundle, Job
from app.services.bundle_service import BundleService
from app.services.storage_service import StorageService
from app.services.export_service import ExportService


class ConcatService:
    def __init__(self, db: AsyncSession, storage: StorageService):
        self.db = db
        self.storage = storage
        self.bundle_service = BundleService(db)
        self.export_service = ExportService(db, storage)

    async def create_concat_job(
        self, title: str, items: List[Dict], silence_ms: int = 100
    ) -> int:
        """Create a concatenation job"""
        job = Job(
            type="concat",
            status="pending",
            input_params=json.dumps({
                "title": title,
                "items": items,
                "silence_ms": silence_ms,
            }),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return job.id

    async def process_concat_job(self, job_id: int) -> int:
        """Process concatenation job and return new bundle_id"""
        job = await self.db.get(Job, job_id)
        if not job:
            raise ValueError("Job not found")

        try:
            job.status = "processing"
            await self.db.commit()

            params = json.loads(job.input_params)
            title = params["title"]
            items = params["items"]
            silence_ms = params.get("silence_ms", 100)

            # Collect all segments
            all_segments = []
            source_bundle_ids = []

            for item in items:
                bundle_id = item["bundle_id"]
                segments = item.get("segments", [])

                bundle = await self.db.get(Bundle, bundle_id)
                if not bundle:
                    raise ValueError(f"Bundle {bundle_id} not found")

                source_bundle_ids.append(bundle_id)

                # Download and extract segments
                itts_data = await self.storage.download_file(bundle.s3_key)
                segment_data = self.export_service._extract_segments_from_itts(
                    itts_data, segments
                )
                all_segments.extend(segment_data)

            # Join all segments
            joined_audio = await self.export_service.join_segments(
                all_segments, silence_ms
            )

            # Create new manifest
            manifest = self._create_concat_manifest(title, source_bundle_ids)

            # Create new ITTS file
            itts_data = self._create_itts_file(manifest, joined_audio)

            # Upload and create bundle
            filename = f"{title.replace(' ', '_')}.itts"
            s3_key = await self.storage.upload_file(filename, itts_data, "bundles")

            bundle_response = await self.bundle_service.create_bundle(
                title=title,
                filename=filename,
                s3_key=s3_key,
                manifest_json=json.dumps(manifest),
                mode="combined",
                is_concatenated=True,
                source_bundle_ids=json.dumps(source_bundle_ids),
            )

            # Update job
            job.status = "completed"
            job.result_bundle_id = bundle_response.id
            job.progress = 1.0
            await self.db.commit()

            return bundle_response.id

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()
            raise

    def _create_concat_manifest(self, title: str, source_ids: List[int]) -> Dict:
        """Create manifest for concatenated bundle"""
        return {
            "format": "index-tts-bundle",
            "version": "1.0.0",
            "bundle_id": title,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "prompt": {"text": f"Concatenated from bundles: {source_ids}"},
            "playback": {
                "default_source": "combined",
                "fallback_order": ["combined"],
                "segment_order": "index_asc",
            },
            "generated_audio": {"mode": "combined"},
            "reference_audio": {"path": "", "mime_type": "audio/wav", "title": "concat"},
            "emotion_audio": {"path": "", "mime_type": "audio/wav", "title": "concat"},
            "generator": {"app": "ITTS Backend", "model": "concat"},
        }

    def _create_itts_file(self, manifest: Dict, audio_data: bytes) -> bytes:
        """Create ITTS file in memory"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("audio/generated/combined.wav", audio_data)
        return buffer.getvalue()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_concat_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/concat_service.py tests/unit/test_concat_service.py
git commit -m "feat: add concatenation service for merging bundles"
```

---

### Task 13: Concatenation API Endpoint

**Files:**
- Modify: `app/api/export.py`

**Step 1: Write failing test**

Add to `tests/integration/test_export_workflow.py`:

```python
@pytest.mark.asyncio
async def test_concat_workflow(test_db_session, mock_minio):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload bundles first
        with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
            r1 = await client.post(
                "/api/bundles",
                files={"file": ("test1.itts", f, "application/octet-stream")}
            )
        bundle_id_1 = r1.json()["id"]

        with open("tests/fixtures/spk_1772197204_1772197238887.itts", "rb") as f:
            r2 = await client.post(
                "/api/bundles",
                files={"file": ("test2.itts", f, "application/octet-stream")}
            )
        bundle_id_2 = r2.json()["id"]

        # Create concat
        response = await client.post(
            "/api/concat",
            json={
                "title": "Test Concat",
                "items": [
                    {"bundle_id": bundle_id_1, "segments": [0]},
                    {"bundle_id": bundle_id_2, "segments": [0]},
                ],
                "silence_ms": 100,
            },
        )

        assert response.status_code == 201
        job_id = response.json()["job_id"]
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_export_workflow.py::test_concat_workflow -v
```

Expected: FAIL with "404 Not Found"

**Step 3: Implement concat endpoint**

Add to `app/api/export.py`:

```python
from app.services.concat_service import ConcatService


@router.post("/concat", status_code=status.HTTP_201_CREATED)
async def create_concat(
    request: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a concatenated bundle"""
    title = request.get("title")
    items = request.get("items", [])
    silence_ms = request.get("silence_ms", 100)

    storage = StorageService()
    service = ConcatService(db, storage)

    job_id = await service.create_concat_job(title, items, silence_ms)

    # Process in background
    background_tasks.add_task(service.process_concat_job, job_id)

    return {"job_id": job_id}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/integration/test_export_workflow.py::test_concat_workflow -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_export_workflow.py
git commit -m "feat: add concatenation endpoint"
```

---

## Phase 6: Remaining Features

### Task 14: Playlists Endpoint

**Files:**
- Create: `app/api/playlists.py`
- Modify: `app/main.py`

**Step 1: Create playlists endpoint**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.database import Playlist, PlaylistEntry, Bundle
from app.models.schemas import PlaylistResponse, BundleResponse

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(db: AsyncSession = Depends(get_db)):
    """List all playlists"""
    result = await db.execute(select(Playlist).order_by(Playlist.name))
    playlists = result.scalars().all()
    return [PlaylistResponse.model_validate(p) for p in playlists]


@router.get("/{playlist_id}/bundles", response_model=list[BundleResponse])
async def get_playlist_bundles(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get bundles in a playlist"""
    result = await db.execute(
        select(Bundle)
        .join(PlaylistEntry, Bundle.id == PlaylistEntry.bundle_id)
        .where(PlaylistEntry.playlist_id == playlist_id)
        .order_by(PlaylistEntry.added_at)
    )
    bundles = result.scalars().all()
    return [BundleResponse.model_validate(b) for b in bundles]


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Create a manual playlist"""
    playlist = Playlist(name=name, is_auto_generated=False)
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return PlaylistResponse.model_validate(playlist)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a playlist"""
    playlist = await db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    await db.delete(playlist)
    await db.commit()
    return None
```

**Step 2: Register router in main.py**

Add to `app/main.py`:
```python
from app.api.playlists import router as playlists_router

app.include_router(playlists_router)
```

**Step 3: Commit**

```bash
git add app/api/playlists.py app/main.py
git commit -m "feat: add playlists endpoints"
```

---

### Task 15: Search Endpoint

**Files:**
- Create: `app/api/search.py`
- Modify: `app/main.py`

**Step 1: Create search endpoint**

```python
from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.models.database import Bundle
from app.models.schemas import BundleResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[BundleResponse])
async def search_bundles(
    q: str | None = Query(None, description="Full-text search query"),
    ref: str | None = Query(None, description="Filter by reference voice"),
    emotion: str | None = Query(None, description="Filter by emotion voice"),
    db: AsyncSession = Depends(get_db),
):
    """Search bundles with filters"""
    query = select(Bundle)

    conditions = []

    if q:
        conditions.append(Bundle.title.contains(q))

    if ref:
        conditions.append(Bundle.reference_voice == ref)

    if emotion:
        conditions.append(Bundle.emotion_voice == emotion)

    if conditions:
        query = query.where(or_(*conditions))

    result = await db.execute(query.order_by(Bundle.created_at.desc()))
    bundles = result.scalars().all()
    return [BundleResponse.model_validate(b) for b in bundles]
```

**Step 2: Register router in main.py**

Add to `app/main.py`:
```python
from app.api.search import router as search_router

app.include_router(search_router)
```

**Step 3: Commit**

```bash
git add app/api/search.py app/main.py
git commit -m "feat: add search endpoint with filters"
```

---

### Task 16: Backup & Restore Service

**Files:**
- Create: `app/services/backup_service.py`
- Create: `tests/unit/test_backup_service.py`

**Step 1: Write failing test**

Create `tests/unit/test_backup_service.py`:

```python
import pytest
from unittest.mock import Mock, patch
from app.services.backup_service import BackupService


@pytest.mark.asyncio
async def test_create_backup():
    mock_db = Mock()
    mock_storage = Mock()

    with patch("app.services.backup_service.tarfile"):
        service = BackupService(mock_db, mock_storage)
        result = await service.create_backup()
        assert result is not None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_backup_service.py -v
```

Expected: FAIL with "BackupService does not exist"

**Step 3: Implement backup service**

Create `app/services/backup_service.py`:

```python
import os
import tarfile
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.storage_service import StorageService
from app.config import settings


class BackupService:
    def __init__(self, db: AsyncSession, storage: StorageService):
        self.db = db
        self.storage = storage

    async def create_backup(self) -> str:
        """Create full backup (DB + MinIO data)"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        backup_filename = f"itts-backup-{timestamp}.tar.gz"

        # Create backup in memory
        buffer = io.BytesIO()

        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Add SQLite database
            db_path = settings.database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                tar.add(db_path, arcname="database/itts.db")

            # Add metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "bundle_count": await self._count_bundles(),
            }
            metadata_bytes = json.dumps(metadata, indent=2).encode()
            metadata_file = io.BytesIO(metadata_bytes)
            tarinfo = tarfile.TarInfo("metadata.json")
            tarinfo.size = len(metadata_bytes)
            tar.addfile(tarinfo, metadata_file)

        # Upload backup to MinIO
        buffer.seek(0)
        await self.storage.upload_file(backup_filename, buffer.getvalue(), "backups")

        return backup_filename

    async def list_backups(self) -> List[str]:
        """List available backups"""
        # This would require MinIO list objects - simplified for now
        return []

    async def restore_backup(self, backup_data: bytes) -> dict:
        """Restore from backup data"""
        buffer = io.BytesIO(backup_data)

        with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
            # Extract database
            db_path = settings.database_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

            for member in tar.getmembers():
                if member.name.startswith("database/"):
                    member.name = member.name.replace("database/", "")
                    tar.extract(member, path=os.path.dirname(db_path) or ".")

            # Read metadata
            metadata_member = tar.extractfile("metadata.json")
            metadata = json.loads(metadata_member.read())

        return {
            "bundles_restored": metadata.get("bundle_count", 0),
            "timestamp": metadata.get("timestamp"),
        }

    async def _count_bundles(self) -> int:
        """Count total bundles in database"""
        from sqlalchemy import select, func
        from app.models.database import Bundle

        result = await self.db.execute(select(func.count()).select_from(Bundle))
        return result.scalar()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_backup_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/backup_service.py tests/unit/test_backup_service.py
git commit -m "feat: add backup service"
```

---

### Task 17: Backup API Endpoint

**Files:**
- Create: `app/api/backup.py`
- Modify: `app/main.py`

**Step 1: Create backup endpoint**

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.db.session import get_db
from app.services.backup_service import BackupService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api", tags=["backup"])


@router.post("/backup")
async def create_backup(db: AsyncSession = Depends(get_db)):
    """Create a manual backup"""
    storage = StorageService()
    service = BackupService(db, storage)

    filename = await service.create_backup()

    return {"filename": filename, "created_at": filename.replace("itts-backup-", "").replace(".tar.gz", "")}


@router.get("/backups")
async def list_backups():
    """List available backups"""
    # Simplified - would need MinIO list implementation
    return {"backups": []}


@router.post("/restore")
async def restore_backup(
    backup: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """Restore from backup file"""
    backup_data = await backup.read()

    storage = StorageService()
    service = BackupService(db, storage)

    result = await service.restore_backup(backup_data)

    return result
```

**Step 2: Register router in main.py**

Add to `app/main.py`:
```python
from app.api.backup import router as backup_router

app.include_router(backup_router)
```

**Step 3: Commit**

```bash
git add app/api/backup.py app/main.py
git commit -m "feat: add backup and restore endpoints"
```

---

## Phase 7: Testing & Documentation

### Task 18: Manual Test Script

**Files:**
- Create: `scripts/manual_test.sh`

**Step 1: Create manual test script**

```bash
#!/bin/bash
# scripts/manual_test.sh

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "=== ITTS Backend Manual Test Suite ==="

# 1. Health check
echo "[1] Health check..."
curl -s "$API_URL/health" | jq '.'

# 2. Upload bundle
echo "[2] Uploading sample ITTS..."
UPLOAD=$(curl -s -X POST "$API_URL/api/bundles" \
  -F "file=@tests/fixtures/spk_1772197182_1772197202988.itts")
BUNDLE_ID=$(echo $UPLOAD | jq -r '.id')
echo "✓ Uploaded bundle ID: $BUNDLE_ID"

# 3. List bundles
echo "[3] Listing all bundles..."
curl -s "$API_URL/api/bundles" | jq '.'

# 4. Get bundle
echo "[4] Getting bundle $BUNDLE_ID..."
curl -s "$API_URL/api/bundles/$BUNDLE_ID" | jq '.'

# 5. Get segments
echo "[5] Getting segments..."
curl -s "$API_URL/api/bundles/$BUNDLE_ID/segments" | jq '.'

# 6. Search
echo "[6] Searching for 'sample1'..."
curl -s "$API_URL/api/search?emotion=sample1" | jq '.'

# 7. List playlists
echo "[7] Listing playlists..."
curl -s "$API_URL/api/playlists" | jq '.'

# 8. Create export
echo "[8] Creating export..."
EXPORT=$(curl -s -X POST "$API_URL/api/export" \
  -H "Content-Type: application/json" \
  -d "{\"bundle_id\": $BUNDLE_ID, \"segment_indices\": [0], \"silence_ms\": 100}")
JOB_ID=$(echo $EXPORT | jq -r '.job_id')
echo "✓ Export job created: $JOB_ID"

# 9. Poll for completion
echo "[9] Waiting for export to complete..."
for i in {1..10}; do
  STATUS=$(curl -s "$API_URL/api/jobs/$JOB_ID" | jq -r '.status')
  if [ "$STATUS" == "completed" ]; then
    echo "✓ Export completed"
    break
  fi
  sleep 1
done

# 10. List backups
echo "[10] Listing backups..."
curl -s "$API_URL/api/backups" | jq '.'

echo "=== All tests passed ==="
```

**Step 2: Make script executable**

```bash
chmod +x scripts/manual_test.sh
```

**Step 3: Commit**

```bash
git add scripts/manual_test.sh
git commit -m "test: add manual test script"
```

---

### Task 19: Update README

**Files:**
- Create: `README.md`

**Step 1: Create README**

```markdown
# ITTS Backend

Backend service for managing ITTS (IndexTTS Bundle) files.

## Features

- Upload and manage ITTS bundles
- Pack raw audio files into ITTS format
- Export custom segment selections as WAV
- Concatenate multiple bundles
- Full-text search and filtering
- Auto-playlists grouped by reference/emotion voices
- Backup and restore

## Quick Start

### Prerequisites

- Docker and Docker Compose
- uv (Python package manager)

### Development Setup

```bash
# Install dependencies
uv sync

# Start services
docker-compose up -d

# Run tests
uv run pytest

# Manual testing
./scripts/manual_test.sh
```

### API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

### Environment Variables

See `.env.example` for configuration options.

## Project Structure

- `app/api/` - FastAPI endpoints
- `app/models/` - Database models and schemas
- `app/services/` - Business logic
- `bundle_tools/` - ITTS format utilities
- `tests/` - Unit and integration tests
- `scripts/` - Manual test scripts

## Design

See [docs/plans/2026-02-28-itts-backend-design.md](docs/plans/2026-02-28-itts-backend-design.md) for detailed design documentation.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick start guide"
```

---

## Phase 8: Final Steps

### Task 20: Final Integration Tests

**Files:**
- Update: `tests/integration/test_backup_restore.py`
- Create: `tests/integration/test_full_workflow.py`

**Step 1: Create comprehensive integration test**

Create `tests/integration/test_full_workflow.py`:

```python
import pytest
import asyncio
import io
import zipfile
import json
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_full_workflow(test_db_session, mock_minio):
    """Test complete workflow: upload, pack, export, search"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload ITTS
        with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
            r1 = await client.post(
                "/api/bundles",
                files={"file": ("test.itts", f, "application/octet-stream")}
            )
        assert r1.status_code == 201
        bundle_id = r1.json()["id"]

        # 2. List bundles
        r2 = await client.get("/api/bundles")
        assert r2.status_code == 200
        assert len(r2.json()["items"]) >= 1

        # 3. Search by emotion
        r3 = await client.get("/api/search?emotion=sample1")
        assert r3.status_code == 200
        assert len(r3.json()) >= 1

        # 4. Get segments
        r4 = await client.get(f"/api/bundles/{bundle_id}/segments")
        assert r4.status_code == 200

        # 5. Create export
        r5 = await client.post(
            "/api/export",
            json={"bundle_id": bundle_id, "segment_indices": [0], "silence_ms": 100},
        )
        assert r5.status_code == 201
        job_id = r5.json()["job_id"]

        # 6. Poll for job completion
        for _ in range(10):
            r6 = await client.get(f"/api/jobs/{job_id}")
            if r6.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("Export job did not complete")

        # 7. List playlists
        r7 = await client.get("/api/playlists")
        assert r7.status_code == 200
        playlists = r7.json()
        assert any(p["name"] == "Main" for p in playlists)


@pytest.mark.asyncio
async def test_duplicate_detection(test_db_session, mock_minio):
    """Test duplicate detection on upload"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload same file twice
        with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
            r1 = await client.post(
                "/api/bundles",
                files={"file": ("test.itts", f, "application/octet-stream")}
            )
        assert r1.status_code == 201

        f.seek(0)
        r2 = await client.post(
            "/api/bundles",
            files={"file": ("test.itts", f, "application/octet-stream")}
        )
        assert r2.status_code == 409
        assert r2.json()["detail"]["status"] == "duplicate"
```

**Step 2: Run all tests**

```bash
uv run pytest -v --cov=app --cov-report=html
```

**Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: add comprehensive integration tests"
```

---

### Task 21: Docker Healthcheck

**Files:**
- Update: `Dockerfile`
- Update: `docker-compose.yml`

**Step 1: Add healthcheck to Dockerfile**

```dockerfile
# Add after EXPOSE
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD uv run python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1
```

**Step 2: Update docker-compose with healthcheck**

```yaml
services:
  itts-api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Step 3: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Docker healthcheck"
```

---

### Task 22: Final Validation

**Step 1: Run full test suite**

```bash
# Unit tests
uv run pytest tests/unit/ -v

# Integration tests
uv run pytest tests/integration/ -v

# Coverage
uv run pytest --cov=app --cov-report=term-missing
```

**Step 2: Manual validation**

```bash
# Start services
docker-compose up -d

# Run manual tests
./scripts/manual_test.sh

# Check API docs
curl http://localhost:8000/docs
```

**Step 3: Update .gitignore if needed**

Review and add any missing patterns:
```gitignore
# Add if needed
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
```

**Step 4: Final commit**

```bash
git add .
git commit -m "chore: final cleanup and validation"
```

---

## Summary

This implementation plan covers:

1. ✅ Project initialization with uv
2. ✅ Docker setup with MinIO
3. ✅ Database models and schemas
4. ✅ Storage service
5. ✅ Bundle CRUD endpoints
6. ✅ Pack endpoint for raw files
7. ✅ Export with async jobs
8. ✅ Concatenation service
9. ✅ Playlists
10. ✅ Search and filters
11. ✅ Backup and restore
12. ✅ Comprehensive testing
13. ✅ Documentation

**Total tasks:** 22
**Estimated time:** 8-12 hours of focused development
**Code review points:** 8 phase gates

---

## For Code Reviewers

**When reviewing Codex AI's implementation:**

1. **Check phase gates** - Use checklists in design document Appendix
2. **Verify reuse of bundle_tools** - No duplicate SHA-256 or path validation code
3. **Test security** - Try path traversal, large file uploads, malformed manifests
4. **Test async patterns** - Ensure no blocking I/O in async functions
5. **Verify error handling** - All endpoints handle edge cases (404, 409, 413, 422)
6. **Check database** - Foreign keys work, cascade deletes work, unique constraints enforced
7. **Run manual tests** - Execute `scripts/manual_test.sh` end-to-end
8. **Review commit history** - Each task should have its own commit with descriptive message

**Red flags to watch for:**
- Reimplementing `bundle_tools` functions (should import, not rewrite)
- Loading full .itts files into memory (should stream)
- Bare `except:` clauses
- Hardcoded paths or credentials
- Missing type hints
- No tests for new code
- Commit messages like "fix" or "update" (should be descriptive)
- **Too few commits** (should be ~30-40 commits for entire project)
- **Large commits** (each step should be separate)
- **Missing tests in commits** (test and implementation should be separate commits)

**Quick validation commands:**
```bash
# All tests pass?
uv run pytest -v

# Coverage acceptable?
uv run pytest --cov=app --cov-report=term-missing

# Docker builds?
docker-compose build

# Manual tests pass?
./scripts/manual_test.sh

# No obvious security issues?
# Try: upload a file with ../../../etc/passwd in manifest paths
# Try: upload a 100MB file
# Try: upload a .itts with invalid JSON
```

---

## For Codex AI (Implementer)

**Follow this plan in order:**
1. Complete tasks 1-3 (Foundation)
2. ⚠️ **STOP** - Commit phase, request Phase 1 review
3. Complete tasks 4-5 (Models)
4. ⚠️ **STOP** - Commit phase, request Phase 2 review
5. Continue phase-by-phase with reviews between

**CRITICAL: Commit frequently!**
- ✅ Commit after EACH STEP (test write, test run, implementation, test run)
- ✅ Commit after EACH TASK when all steps pass
- ✅ Commit after EACH PHASE with detailed summary
- ❌ DON'T wait until end of phase to commit
- ❌ DON'T batch multiple unrelated changes in one commit

**Commit message format:**
```bash
# After a step within a task
git add app/models/database.py tests/unit/test_models.py
git commit -m "feat: add Bundle model with SHA-256 unique constraint"

# After completing a full task
git add app/services/bundle_service.py tests/unit/test_bundle_service.py
git commit -m "feat: implement bundle service with CRUD operations

- Added create_bundle() method
- Added check_duplicate() for SHA-256 deduplication
- Implemented auto-playlist creation
- Added unit tests with mocked dependencies
- All tests passing
"

# After completing a full phase
git add app/api/ app/models/ tests/
git commit -m "feat(phase): complete API endpoints phase

- Implemented bundle upload endpoint
- Added pack endpoint for raw files
- Added export and concat endpoints
- Implemented error handling (404, 409, 422)
- Added integration tests
- All phase gate criteria met
"
```

**After each phase:**
- Run all tests: `uv run pytest -v`
- Run manual tests: `./scripts/manual_test.sh`
- Commit the phase with detailed summary
- Request code review before proceeding
- Address any review feedback before next phase

**Getting stuck?**
- Check design document for architecture decisions
- Check bundle_tools/ for existing utilities to reuse
- Check test fixtures for expected behavior
- Ask questions rather than making assumptions

---

### Test Fixtures Reference

**Available test fixtures:**
- `tests/fixtures/spk_1772197182_1772197202988.itts` - For testing `/api/bundles/pack`
  - SHA-256: `19794afc2ba65a8e296e7738bd437d1dca609658b9282453838d8024a8bcc1e2`
  - Reference: `[wls]现在微商叫轻资产创业招募...`
  - Emotion: `sample1`
  - Mode: `combined`
  - 2 segments

- `tests/fixtures/spk_1772197204_1772197238887.itts` - For testing `/api/bundles`
  - SHA-256: `3b9eb25993e4222cb37541830179fc21c2f051b9563072e239485bd3cb9d3d85`
  - Reference: `[wls]现在微商叫轻资产创业招募...` (same as above)
  - Emotion: `sample1` (same as above)
  - Mode: `combined`
  - 3 segments

**Key insight:** Both files have the same reference and emotion voices, but different generated audio (different SHA-256). This allows testing:
1. Different bundles can have same reference/emotion (not duplicates)
2. Duplicate detection only triggers on same generated audio SHA-256

---

## Quick Reference Card

### ⚡ Quick Commands

```bash
# Review latest commit
git log -1 --patch

# Show what changed
git diff HEAD~1 HEAD

# Run tests
uv run pytest -v

# Check coverage
uv run pytest --cov=app --cov-report=term-missing
```

### 📋 Review Checklist (Fast Version)

- [ ] Tests pass?
- [ ] Type hints present?
- [ ] No hardcoded paths?
- [ ] Proper error handling?
- [ ] Commits frequent and descriptive?

### 🚨 Red Flags (Instant Reject)

- Bare `except:` clauses
- No type hints
- Hardcoded credentials
- Reimplementing `bundle_tools`
- Loading full files in memory
- Missing tests

### ✅ Green Flags (Good to Go)

- Reuses `bundle_tools.itts_common`
- Async with proper context managers
- Streaming large files
- Descriptive commit messages
- Test + implementation separate commits

### 🔄 Review Cycle Summary

1. **Codex completes step** → stops
2. **You**: "Claude, review latest commit"
3. **Claude**: Provides detailed review (APPROVED / NEEDS FIXES / CRITICAL)
4. **You**: Paste feedback to Codex
5. **Codex**: Fixes and commits
6. **Repeat until APPROVED**
7. **Proceed to next step**

---
