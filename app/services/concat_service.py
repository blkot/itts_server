import io
import json
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Bundle, Job
from app.models.schemas import BundleResponse
from app.services.bundle_service import BundleService
from app.services.export_service import ExportService
from app.services.storage_service import StorageService
from bundle_tools.itts_common import (
    now_utc_iso,
    sha256_bytes,
    validate_manifest_with_schema,
    validate_segment_index_contract,
)


class ConcatService:
    def __init__(self, db: AsyncSession, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.bundle_service = BundleService(db)
        self.export_service = ExportService(db, storage)

    async def create_concat_job(self, title: str, items: list[dict], silence_ms: int = 100) -> int:
        """Create a concat job and return job_id."""
        job = Job(
            type="concat",
            status="pending",
            input_params=json.dumps(
                {
                    "title": title,
                    "items": items,
                    "silence_ms": silence_ms,
                }
            ),
            progress=0.0,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job.id

    async def process_concat_job(self, job_id: int) -> int:
        """Process a concat job and return resulting bundle id."""
        job = await self.db.get(Job, job_id)
        if job is None:
            raise ValueError("Job not found")

        try:
            job.status = "processing"
            job.progress = 0.1
            await self.db.commit()

            params = json.loads(job.input_params)
            bundle = await self.create_concat_bundles(
                title=str(params["title"]),
                items=list(params.get("items", [])),
                silence_ms=int(params.get("silence_ms", 100)),
            )

            job.status = "completed"
            job.progress = 1.0
            job.result_bundle_id = bundle.id
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return bundle.id
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise

    async def create_concat_bundles(
        self,
        title: str,
        items: list[dict],
        silence_ms: int = 100,
    ) -> BundleResponse:
        """Concatenate selected segments from multiple bundles into a new ITTS bundle."""
        all_segments, source_bundle_ids = await self._collect_segments(items)
        joined_audio = await self.export_service.join_segments(all_segments, silence_ms=silence_ms)

        generated_sha256 = sha256_bytes(joined_audio)
        duplicate = await self.bundle_service.check_duplicate(generated_sha256)
        if duplicate is not None:
            return self.bundle_service._bundle_to_response(duplicate)

        manifest = self._create_concat_manifest(
            title=title,
            source_ids=source_bundle_ids,
            joined_audio=joined_audio,
            generated_sha256=generated_sha256,
        )

        schema_path = Path(__file__).resolve().parents[2] / "docs" / "bundle.schema.json"
        validate_manifest_with_schema(manifest, schema_path, strict_schema=False)
        validate_segment_index_contract(manifest)

        itts_data = self._create_itts_file(manifest, joined_audio)
        filename = f"{self._safe_slug(title)}.itts"
        s3_key = await self.storage.upload_file(filename, itts_data, prefix="bundles")

        bundle_response = await self.bundle_service.create_bundle(
            title=title,
            filename=filename,
            s3_key=s3_key,
            manifest_json=json.dumps(manifest, ensure_ascii=False),
            generated_audio_sha256=generated_sha256,
            reference_voice="concat",
            emotion_voice="concat",
            mode="combined",
            is_concatenated=True,
            source_bundle_ids=json.dumps(source_bundle_ids),
        )

        # Keep concatenated outputs discoverable.
        await self.bundle_service._get_or_create_playlist(
            name="Concats",
            is_auto_generated=True,
            auto_type="concat",
            auto_value="concat",
        )
        await self.bundle_service._add_to_playlist(bundle_response.id, "Concats")
        await self.db.commit()

        return bundle_response

    async def _collect_segments(
        self,
        items: list[dict],
    ) -> tuple[list[tuple[bytes, int, int | None]], list[int]]:
        all_segments: list[tuple[bytes, int, int | None]] = []
        source_ids: list[int] = []

        for item in items:
            bundle_id = int(item["bundle_id"])
            segment_indices = [int(idx) for idx in item.get("segments", [])]

            bundle = await self.db.get(Bundle, bundle_id)
            if bundle is None:
                raise ValueError(f"Bundle {bundle_id} not found")

            source_ids.append(bundle_id)
            itts_data = await self.storage.download_file(bundle.s3_key)
            segment_data = self.export_service._extract_segments_from_itts(itts_data, segment_indices)
            all_segments.extend(segment_data)

        if not all_segments:
            raise ValueError("No segments found for concatenation")

        return all_segments, source_ids

    @staticmethod
    def _create_concat_manifest(
        title: str,
        source_ids: list[int],
        joined_audio: bytes,
        generated_sha256: str,
    ) -> dict[str, Any]:
        shared_sha = sha256_bytes(joined_audio)
        return {
            "format": "index-tts-bundle",
            "version": "1.1.0",
            "bundle_id": str(uuid.uuid4()),
            "created_at": now_utc_iso(),
            "prompt": {
                "text": f"Concatenated from bundles: {source_ids}",
            },
            "playback": {
                "default_source": "combined",
                "fallback_order": ["combined"],
                "segment_order": "index_asc",
            },
            "generated_audio": {
                "mode": "combined",
                "combined": {
                    "path": "audio/generated/combined.wav",
                    "mime_type": "audio/wav",
                    "sha256": generated_sha256,
                    "bytes": len(joined_audio),
                },
            },
            "reference_audio": {
                "title": "concat",
                "path": "audio/reference.wav",
                "mime_type": "audio/wav",
                "sha256": shared_sha,
                "bytes": len(joined_audio),
            },
            "emotion_audio": {
                "title": "concat",
                "path": "audio/emotion.wav",
                "mime_type": "audio/wav",
                "sha256": shared_sha,
                "bytes": len(joined_audio),
            },
            "generator": {
                "app": "ITTS Backend",
                "model": "concat",
                "settings": {
                    "source_bundle_ids": source_ids,
                    "title": title,
                },
            },
        }

    @staticmethod
    def _create_itts_file(manifest: dict[str, Any], audio_data: bytes) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("audio/generated/combined.wav", audio_data)
            archive.writestr("audio/reference.wav", audio_data)
            archive.writestr("audio/emotion.wav", audio_data)
        return buffer.getvalue()

    @staticmethod
    def _safe_slug(title: str) -> str:
        value = re.sub(r"[^A-Za-z0-9._-]+", "_", title.strip())
        value = value.strip("._")
        return value or "concat_bundle"
