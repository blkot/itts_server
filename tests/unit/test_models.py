import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Bundle, Playlist, User


@pytest.mark.asyncio
async def test_create_bundle(db_session: AsyncSession) -> None:
    bundle = Bundle(
        title="Test Bundle",
        filename="test.itts",
        s3_key="bundles/test.itts",
        manifest_json='{"format": "index-tts-bundle"}',
        generated_audio_sha256="abc123",
        reference_voice="voice1",
        emotion_voice="happy",
        mode="combined",
        total_duration_ms=5000,
    )
    db_session.add(bundle)
    await db_session.commit()
    await db_session.refresh(bundle)

    assert bundle.id is not None
    assert bundle.title == "Test Bundle"


@pytest.mark.asyncio
async def test_create_auto_playlist(db_session: AsyncSession) -> None:
    playlist = Playlist(
        name="voice1",
        is_auto_generated=True,
        auto_type="reference",
        auto_value="voice1",
    )
    db_session.add(playlist)
    await db_session.commit()
    await db_session.refresh(playlist)

    assert playlist.id is not None
    assert playlist.auto_type == "reference"
