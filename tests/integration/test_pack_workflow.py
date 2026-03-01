import io
import json
import zipfile
from unittest.mock import Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_pack_from_raw_files(db_session) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    mock_minio = Mock()
    mock_minio.put_object = Mock()

    try:
        with open("tests/fixtures/spk_1772197182_1772197202988.itts", "rb") as f:
            itts_data = f.read()

        with zipfile.ZipFile(io.BytesIO(itts_data)) as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            combined_path = manifest["generated_audio"]["combined"]["path"]
            reference_path = manifest["reference_audio"]["path"]
            emotion_path = manifest["emotion_audio"]["path"]
            combined = zf.read(combined_path)
            reference = zf.read(reference_path)
            emotion = zf.read(emotion_path)

        with patch("app.services.storage_service.get_minio_client", return_value=mock_minio):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/bundles/pack",
                    data={
                        "title": "Test Pack",
                        "prompt_text": manifest["prompt"]["text"],
                        "reference_title": manifest["reference_audio"]["title"],
                        "emotion_title": manifest["emotion_audio"]["title"],
                    },
                    files={
                        "generated_combined": ("combined.wav", io.BytesIO(combined), "audio/wav"),
                        "reference_audio": ("reference.wav", io.BytesIO(reference), "audio/wav"),
                        "emotion_audio": ("emotion.wav", io.BytesIO(emotion), "audio/wav"),
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
    finally:
        app.dependency_overrides.clear()
