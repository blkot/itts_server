from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.backup_service import BackupService


@pytest.mark.asyncio
async def test_create_backup() -> None:
    mock_db = Mock()
    mock_result = Mock()
    mock_result.scalar.return_value = 2
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_storage = Mock()
    mock_storage.upload_file = AsyncMock()

    with patch("app.services.backup_service.tarfile"):
        service = BackupService(mock_db, mock_storage)
        result = await service.create_backup()

    assert result.startswith("itts-backup-")
    mock_storage.upload_file.assert_awaited_once()
