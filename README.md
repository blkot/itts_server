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
