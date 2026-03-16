from unittest.mock import Mock, patch

import pytest

from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_upload_file() -> None:
    mock_minio = Mock()
    with patch("app.services.storage_service.get_minio_client", return_value=mock_minio):
        service = StorageService()
        await service.upload_file("test.itts", b"fake data", "bundles/")

        mock_minio.put_object.assert_called_once()
