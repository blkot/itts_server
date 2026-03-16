from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_backup_endpoints(db_session) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with (
            patch(
                "app.api.backup.BackupService.create_backup",
                new=AsyncMock(return_value="itts-backup-2026-03-02.tar.gz"),
            ),
            patch(
                "app.api.backup.BackupService.list_backups",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.api.backup.BackupService.restore_backup",
                new=AsyncMock(
                    return_value={
                        "bundles_restored": 2,
                        "timestamp": "2026-03-02T00:00:00Z",
                    }
                ),
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                create_resp = await client.post("/api/backup")
                assert create_resp.status_code == 200
                assert create_resp.json() == {
                    "filename": "itts-backup-2026-03-02.tar.gz",
                    "created_at": "2026-03-02",
                }

                list_resp = await client.get("/api/backups")
                assert list_resp.status_code == 200
                assert list_resp.json() == {"backups": []}

                restore_resp = await client.post(
                    "/api/restore",
                    files={"backup": ("backup.tar.gz", b"fake-data", "application/gzip")},
                )
                assert restore_resp.status_code == 200
                assert restore_resp.json() == {
                    "bundles_restored": 2,
                    "timestamp": "2026-03-02T00:00:00Z",
                }
    finally:
        app.dependency_overrides.clear()
