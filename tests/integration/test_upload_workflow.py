from unittest.mock import Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_upload_itts_success(db_session) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    mock_minio = Mock()
    mock_minio.put_object = Mock()

    try:
        with patch("app.services.storage_service.get_minio_client", return_value=mock_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
                    response = await client.post(
                        "/api/bundles",
                        files={"file": ("test.itts", f, "application/octet-stream")},
                    )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["reference_voice"] == "[wls]现在微商叫轻资产创业招募，你说搞不搞笑，就是又换名字。"
    finally:
        app.dependency_overrides.clear()
