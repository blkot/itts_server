import io
import wave
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.export_service import ExportService


@pytest.mark.asyncio
async def test_join_segments() -> None:
    sample_rate = 22050
    duration = 1
    mock_wav = io.BytesIO()
    with wave.open(mock_wav, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * sample_rate * duration)

    mock_db = Mock()
    mock_storage = Mock()
    mock_storage.download_file = AsyncMock(return_value=mock_wav.getvalue())

    service = ExportService(mock_db, mock_storage)

    mock_segments = [
        Mock(s3_key="seg0.wav", start_ms=0, end_ms=1000),
        Mock(s3_key="seg1.wav", start_ms=1000, end_ms=2000),
    ]

    result = await service.join_segments(mock_segments, silence_ms=100)

    assert result is not None
    assert len(result) > 0
