# Contributing to ITTS Backend

Thank you for contributing.

## Getting Started

### Prerequisites

- Python 3.11
- `uv`
- Docker and Docker Compose

### Development Setup

1. Clone the repository.
2. Install dependencies with `uv sync --dev`.
3. Start local services with `docker-compose up -d --build`.
4. Initialize the database with `docker-compose exec -T itts-api uv run python -c "import asyncio; from app.db.init_db import init_db; asyncio.run(init_db())"`.

## Branch Workflow

- `develop` is the default branch for active development.
- `main` is reserved for stable releases.
- Create feature branches from `develop` for non-trivial work.

## Code Style

- Follow PEP 8.
- Keep type hints on public functions.
- Prefer small, focused commits with conventional commit messages.
- Run `uv run ruff check app/` before opening a pull request.

## Testing

The public repository includes the Python test suite, but it does not include private binary fixture `.itts` files.

- Run the committed test suite before submitting changes.
- Use `scripts/manual_test.sh` or `scripts/manual_test.ps1` with `ITTS_SAMPLE_PATH` pointing to a local `.itts` file.
- Integration tests use generated sample bundles, so they do not depend on committed private media files.

## Pull Requests

Before submitting a pull request:

- Ensure the code builds locally.
- Update documentation when behavior changes.
- Explain the user-visible impact.
- Call out any follow-up work or known limitations.

Open pull requests against `develop` unless the change is explicitly a release-only change.

## Security Issues

Do not open public issues for security vulnerabilities. Follow the process in `SECURITY.md`.
