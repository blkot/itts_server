import io
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_pack_from_raw_files(db_session, sample_itts_bundle, fake_minio) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("app.services.storage_service.get_minio_client", return_value=fake_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/bundles/pack",
                    data={
                        "title": "Test Pack",
                        "prompt_text": sample_itts_bundle.prompt_text,
                        "reference_title": sample_itts_bundle.reference_title,
                        "emotion_title": sample_itts_bundle.emotion_title,
                    },
                    files={
                        "generated_combined": (
                            "combined.wav",
                            io.BytesIO(sample_itts_bundle.generated_audio),
                            "audio/wav",
                        ),
                        "reference_audio": (
                            "reference.wav",
                            io.BytesIO(sample_itts_bundle.reference_audio),
                            "audio/wav",
                        ),
                        "emotion_audio": (
                            "emotion.wav",
                            io.BytesIO(sample_itts_bundle.emotion_audio),
                            "audio/wav",
                        ),
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
    finally:
        app.dependency_overrides.clear()
