from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import Bundle, Segment
from app.models.schemas import BundleResponse

router = APIRouter(prefix="/api/search", tags=["search"])


def _dt_to_str(value: datetime) -> str:
    if value.tzinfo is None:
        dt = value.replace(tzinfo=timezone.utc)
    else:
        dt = value.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@router.get("", response_model=list[BundleResponse])
async def search_bundles(
    q: str | None = Query(None, description="Full-text search query"),
    ref: str | None = Query(None, description="Filter by reference voice"),
    emotion: str | None = Query(None, description="Filter by emotion voice"),
    db: AsyncSession = Depends(get_db),
) -> list[BundleResponse]:
    """Search bundles with text and metadata filters."""
    query = select(Bundle)
    conditions = []

    q_text = q.strip() if q else None
    ref_text = ref.strip() if ref else None
    emotion_text = emotion.strip() if emotion else None

    if q_text:
        segment_text_exists = (
            select(Segment.id)
            .where(
                Segment.bundle_id == Bundle.id,
                or_(
                    Segment.text_prompt.contains(q_text),
                    Segment.normalized_text.contains(q_text),
                ),
            )
            .exists()
        )
        conditions.append(
            or_(
                Bundle.title.contains(q_text),
                segment_text_exists,
            )
        )

    if ref_text:
        conditions.append(Bundle.reference_voice == ref_text)

    if emotion_text:
        conditions.append(Bundle.emotion_voice == emotion_text)

    if conditions:
        query = query.where(or_(*conditions))

    result = await db.execute(query.order_by(Bundle.created_at.desc()))
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
