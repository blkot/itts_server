import pytest
from unittest.mock import AsyncMock, Mock

from app.models.schemas import BundleResponse
from app.services.concat_service import ConcatService


@pytest.mark.asyncio
async def test_create_concat_bundle() -> None:
    mock_db = Mock()
    mock_storage = Mock()
    mock_db.get = AsyncMock(
        side_effect=[
            Mock(s3_key="bundle1.itts", manifest_json='{"prompt": {"text": "Hello"}}'),
            Mock(s3_key="bundle2.itts", manifest_json='{"prompt": {"text": "World"}}'),
        ]
    )
    mock_db.commit = AsyncMock()
    mock_storage.download_file = AsyncMock(return_value=b"fake-itts")
    mock_storage.upload_file = AsyncMock(return_value="bundles/concat_test.itts")

    service = ConcatService(mock_db, mock_storage)
    service.export_service._extract_segments_from_itts = Mock(
        return_value=[(b"segment-bytes", 0, 1000)]
    )
    service.export_service.join_segments = AsyncMock(return_value=b"joined-bytes")
    service.bundle_service.check_duplicate = AsyncMock(return_value=None)
    service.bundle_service.create_bundle = AsyncMock(
        return_value=BundleResponse(
            id=123,
            title="Concat Test",
            filename="concat_test.itts",
            s3_key="bundles/concat_test.itts",
            generated_audio_sha256="abc",
            reference_voice="concat",
            emotion_voice="concat",
            mode="combined",
            total_duration_ms=None,
            is_concatenated=True,
            created_at="2026-03-02T00:00:00Z",
        )
    )
    service.bundle_service._get_or_create_playlist = AsyncMock()
    service.bundle_service._add_to_playlist = AsyncMock()

    result = await service.create_concat_bundles(
        title="Concat Test",
        items=[{"bundle_id": 1, "segments": [0]}, {"bundle_id": 2, "segments": [0]}],
        silence_ms=100,
    )

    assert result is not None
    assert result.id == 123
