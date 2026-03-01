from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import Bundle, Playlist, PlaylistEntry
from app.models.schemas import BundleResponse, PlaylistResponse

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


def _dt_to_str(value: datetime) -> str:
    if value.tzinfo is None:
        dt = value.replace(tzinfo=timezone.utc)
    else:
        dt = value.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(db: AsyncSession = Depends(get_db)) -> list[PlaylistResponse]:
    """List all playlists in ascending name order."""
    result = await db.execute(select(Playlist).order_by(Playlist.name.asc()))
    playlists = result.scalars().all()
    return [
        PlaylistResponse(
            id=playlist.id,
            name=playlist.name,
            is_auto_generated=playlist.is_auto_generated,
            auto_type=playlist.auto_type,
            auto_value=playlist.auto_value,
            created_at=_dt_to_str(playlist.created_at),
        )
        for playlist in playlists
    ]


@router.get("/{playlist_id}/bundles", response_model=list[BundleResponse])
async def get_playlist_bundles(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[BundleResponse]:
    """Return bundles that belong to a playlist."""
    playlist = await db.get(Playlist, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    result = await db.execute(
        select(Bundle)
        .join(PlaylistEntry, Bundle.id == PlaylistEntry.bundle_id)
        .where(PlaylistEntry.playlist_id == playlist_id)
        .order_by(PlaylistEntry.added_at.asc())
    )
    bundles = result.scalars().all()
    return [
        BundleResponse(
            id=bundle.id,
            title=bundle.title,
            filename=bundle.filename,
            s3_key=bundle.s3_key,
            generated_audio_sha256=bundle.generated_audio_sha256,
            reference_voice=bundle.reference_voice,
            emotion_voice=bundle.emotion_voice,
            mode=bundle.mode,
            total_duration_ms=bundle.total_duration_ms,
            is_concatenated=bundle.is_concatenated,
            created_at=_dt_to_str(bundle.created_at),
        )
        for bundle in bundles
    ]


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    name: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    """Create a manual playlist."""
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=422, detail="Playlist name cannot be empty")

    playlist = Playlist(name=normalized_name, is_auto_generated=False)
    db.add(playlist)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Playlist already exists") from None

    await db.refresh(playlist)
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        is_auto_generated=playlist.is_auto_generated,
        auto_type=playlist.auto_type,
        auto_value=playlist.auto_value,
        created_at=_dt_to_str(playlist.created_at),
    )


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a playlist."""
    playlist = await db.get(Playlist, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    await db.delete(playlist)
    await db.commit()
