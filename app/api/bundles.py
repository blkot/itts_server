import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import Bundle
from app.models.schemas import BundleListResponse, BundleResponse, SegmentResponse
from app.services.bundle_service import BundleService
from app.services.pack_service import PackService
from app.services.storage_service import StorageService

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 1024 * 1024

router = APIRouter(prefix="/api/bundles", tags=["bundles"])


async def _read_upload_with_limit(file: UploadFile, max_size: int = MAX_UPLOAD_SIZE) -> bytes:
    data = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_size:
            raise HTTPException(status_code=413, detail="File too large")
    await file.seek(0)
    return bytes(data)


def _extract_generated_sha256(manifest: dict) -> str | None:
    generated = manifest.get("generated_audio") or {}
    mode = generated.get("mode")

    if mode in {"combined", "both"}:
        combined = generated.get("combined") or {}
        sha = combined.get("sha256")
        if isinstance(sha, str) and sha:
            return sha

    return None


def _extract_total_duration_ms(manifest: dict) -> int | None:
    generated = manifest.get("generated_audio") or {}
    combined = generated.get("combined") or {}
    raw_duration = combined.get("duration_ms")
    if raw_duration is None:
        return None
    try:
        return int(round(float(raw_duration)))
    except (TypeError, ValueError):
        return None


@router.post("", response_model=BundleResponse, status_code=status.HTTP_201_CREATED)
async def upload_bundle(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> BundleResponse:
    """Upload an existing ITTS bundle and index it in the library."""
    if not file.filename:
        raise HTTPException(status_code=422, detail="Missing filename")

    itts_data = await _read_upload_with_limit(file)

    bundle_service = BundleService(db)
    manifest = bundle_service.extract_manifest_from_itts(itts_data)

    generated_sha256 = _extract_generated_sha256(manifest)

    if not generated_sha256:
        generated = manifest.get("generated_audio") or {}
        combined = generated.get("combined") or {}
        combined_path = combined.get("path")
        if isinstance(combined_path, str) and combined_path:
            try:
                combined_data = bundle_service.extract_file_from_itts(itts_data, combined_path)
            except ValueError:
                combined_data = b""
            if combined_data:
                generated_sha256 = StorageService.calculate_data_sha256(combined_data)

    if generated_sha256:
        duplicate = await bundle_service.check_duplicate(generated_sha256)
        if duplicate:
            existing_bundle = await bundle_service.get_bundle(duplicate.id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "duplicate",
                    "message": "This ITTS already exists in your library",
                    "existing_bundle": (
                        existing_bundle.model_dump() if existing_bundle else {"id": duplicate.id}
                    ),
                },
            )

    storage_service = StorageService()
    s3_key = await storage_service.upload_file(file.filename, itts_data, prefix="bundles")

    manifest_json = json.dumps(manifest, ensure_ascii=False)
    response = await bundle_service.create_bundle(
        title=str(manifest.get("bundle_id") or file.filename),
        filename=file.filename,
        s3_key=s3_key,
        manifest_json=manifest_json,
        generated_audio_sha256=generated_sha256,
        reference_voice=(manifest.get("reference_audio") or {}).get("title"),
        emotion_voice=(manifest.get("emotion_audio") or {}).get("title"),
        mode=(manifest.get("generated_audio") or {}).get("mode"),
        total_duration_ms=_extract_total_duration_ms(manifest),
    )
    return response


@router.get("", response_model=BundleListResponse)
async def list_bundles(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> BundleListResponse:
    service = BundleService(db)
    items = await service.list_bundles(page=page, page_size=page_size)

    result = await db.execute(select(func.count()).select_from(Bundle))
    total = int(result.scalar() or 0)

    return BundleListResponse(total=total, items=items, page=page, page_size=page_size)


@router.post("/pack", response_model=BundleResponse, status_code=status.HTTP_201_CREATED)
async def pack_bundle(
    title: str = Form(...),
    prompt_text: str = Form(...),
    reference_title: str = Form(...),
    emotion_title: str = Form(...),
    generated_combined: UploadFile = File(...),
    reference_audio: UploadFile = File(...),
    emotion_audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> BundleResponse:
    """Pack raw audio files into a new ITTS bundle."""
    generated_data = await _read_upload_with_limit(generated_combined)
    reference_data = await _read_upload_with_limit(reference_audio)
    emotion_data = await _read_upload_with_limit(emotion_audio)

    bundle_service = BundleService(db)
    storage_service = StorageService()
    pack_service = PackService(bundle_service, storage_service)

    result = await pack_service.pack_from_raw_files(
        title=title,
        prompt_text=prompt_text,
        reference_title=reference_title,
        emotion_title=emotion_title,
        generated_combined=generated_data,
        reference_audio=reference_data,
        emotion_audio=emotion_data,
    )

    if result["status"] == "duplicate":
        existing = result["existing_bundle"]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "duplicate",
                "message": "This ITTS already exists in your library",
                "existing_bundle": existing.model_dump(),
            },
        )

    return result["bundle"]


@router.get("/{bundle_id}", response_model=BundleResponse)
async def get_bundle(bundle_id: int, db: AsyncSession = Depends(get_db)) -> BundleResponse:
    service = BundleService(db)
    bundle = await service.get_bundle(bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@router.get("/{bundle_id}/segments", response_model=list[SegmentResponse])
async def get_bundle_segments(bundle_id: int, db: AsyncSession = Depends(get_db)) -> list[SegmentResponse]:
    service = BundleService(db)
    return await service.get_segments(bundle_id)


@router.delete("/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bundle(bundle_id: int, db: AsyncSession = Depends(get_db)) -> None:
    service = BundleService(db)
    deleted = await service.delete_bundle(bundle_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bundle not found")
