from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_upload_itts_success(db_session, sample_itts_bundle, fake_minio) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/bundles",
                    files={"file": (sample_itts_bundle.filename, sample_itts_bundle.data, "application/octet-stream")},
                )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["reference_voice"] == sample_itts_bundle.reference_title
    finally:
        app.dependency_overrides.clear()
