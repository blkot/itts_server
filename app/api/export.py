import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import Export, Job
from app.models.schemas import ExportRequest, JobResponse
from app.services.export_service import ExportService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["export"])


def _dt_to_str(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        dt = value.replace(tzinfo=timezone.utc)
    else:
        dt = value.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


async def _process_export_job_with_logging(service: ExportService, job_id: int) -> None:
    try:
        await service.process_export_job(job_id)
    except Exception:
        logger.exception("Export job failed", extra={"job_id": job_id})


@router.post("/export", status_code=status.HTTP_201_CREATED)
async def create_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    storage = StorageService()
    service = ExportService(db, storage)

    job_id = await service.create_export_job(
        bundle_id=request.bundle_id,
        segment_indices=request.segment_indices,
        silence_ms=request.silence_ms,
    )

    background_tasks.add_task(_process_export_job_with_logging, service, job_id)
    return {"job_id": job_id}


@router.get("/export/{export_id}")
async def download_export(export_id: int, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    export = await db.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")

    storage = StorageService()
    data = await storage.download_file(export.s3_key)

    return StreamingResponse(
        io.BytesIO(data),
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="export_{export_id}.wav"'},
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)) -> JobResponse:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        result_bundle_id=job.result_bundle_id,
        result_export_id=job.result_export_id,
        error_message=job.error_message,
        created_at=_dt_to_str(job.created_at) or "",
        completed_at=_dt_to_str(job.completed_at),
    )
