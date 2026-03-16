from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Bundle
from app.services.bundle_service import BundleService


@pytest.mark.asyncio
async def test_check_duplicate_found() -> None:
    mock_db = Mock(spec=AsyncSession)
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = Bundle(
        id=1,
        title="Existing",
        filename="existing.itts",
        s3_key="bundles/existing.itts",
        manifest_json="{}",
    )
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = BundleService(mock_db)
    duplicate = await service.check_duplicate("abc123")

    assert duplicate is not None
    assert duplicate.id == 1
