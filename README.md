# ITTS Backend

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3110/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)

**Backend-only REST API service** for managing ITTS (IndexTTS Bundle) files.

> **Note:** This is a pure backend project. For frontend development documentation, see [`docs/frontend/`](docs/frontend/README.md). The frontend should be built as a separate project.

## Features

- Upload and manage ITTS bundles
- Pack raw audio files into ITTS format
- Export custom segment selections as WAV
- Concatenate multiple bundles
- Full-text search and filtering
- Auto-playlists grouped by reference/emotion voices
- Backup and restore

## Project Stats

- **Status:** Production-ready backend
- **Runtime:** FastAPI + SQLite + MinIO
- **Lock file:** `uv.lock` committed for reproducible installs
- **Branch model:** `develop` for active work, `main` for releases

## Contributing

Contribution guidelines are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Security reporting guidance is in [SECURITY.md](SECURITY.md).

## Quick Start

### Prerequisites

- Docker and Docker Compose
- uv (Python package manager)

### Development Setup

```bash
# Install dependencies
uv sync --dev

# Start services
docker-compose up -d

# Initialize the database
docker-compose exec -T itts-api uv run python -c "import asyncio; from app.db.init_db import init_db; asyncio.run(init_db())"

# Run manual validation with a local ITTS file
ITTS_SAMPLE_PATH=/path/to/sample.itts ./scripts/manual_test.sh
```

### API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

### Frontend Integration

This backend is designed to work with a separate frontend application.

> **📘 Frontend developers:** Start with [`docs/frontend/PURPOSE.md`](docs/frontend/PURPOSE.md) to understand the architecture, then see [`docs/frontend/README.md`](docs/frontend/README.md) for the complete frontend development guide.

**Frontend documentation includes:**
- API specification with TypeScript types
- User workflows and UI wireframes
- Technical requirements and setup guide
- Feature checklist and development roadmap

### Enabling CORS

**Option 1: Development (Allow all origins)**
```python
# In app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Option 2: Production (Specific origins)**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.com",
        "https://www.your-frontend.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **See [`docs/frontend/`](docs/frontend/README.md)** for complete frontend development documentation, including:
> - API specification with TypeScript types
> - User workflows and UI wireframes
> - Technical requirements and setup guide

### Environment Variables

See `.env.example` for configuration options.

### Private Development Assets

The public repository does not include the private test suite or `.itts` fixture files. For local validation, provide your own sample bundle with `ITTS_SAMPLE_PATH`.

## Project Structure

- `app/api/` - FastAPI endpoints
- `app/models/` - Database models and schemas
- `app/services/` - Business logic
- `bundle_tools/` - ITTS format utilities
- `scripts/` - Manual test scripts
- `docs/frontend/` - Frontend integration reference docs

## Design

See [docs/plans/2026-02-28-itts-backend-design.md](docs/plans/2026-02-28-itts-backend-design.md) for detailed design documentation.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │
│   Frontend      │────────▶│  ITTS Backend   │
│  (Separate      │  HTTP   │   (This Repo)   │
│   Project)      │         │                 │
│                 │         │                 │
└─────────────────┘         └─────────────────┘
                                    │
                                    ▼
                            ┌─────────────────┐
                            │                 │
                            │     MinIO       │
                            │  (S3 Storage)   │
                            │                 │
                            └─────────────────┘
```

This backend provides:
- REST API endpoints for all operations
- SQLite database for metadata
- MinIO/S3 storage for ITTS files
- Background job processing for exports

**Frontend responsibilities** (separate project):
- User interface for browsing/uploading
- Audio player component
- Export configuration UI
- Playlist management UI

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
