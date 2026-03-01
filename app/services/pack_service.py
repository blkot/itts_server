import io
import json
import re
import uuid
import zipfile
from pathlib import Path
from typing import Any

from app.models.schemas import BundleResponse
from app.services.bundle_service import BundleService
from app.services.storage_service import StorageService
from bundle_tools.itts_common import (
    now_utc_iso,
    sha256_bytes,
    validate_manifest_with_schema,
    validate_segment_index_contract,
)


class PackService:
    def __init__(self, bundle_service: BundleService, storage: StorageService) -> None:
        self.bundle_service = bundle_service
        self.storage = storage

    async def pack_from_raw_files(
        self,
        title: str,
        prompt_text: str,
        reference_title: str,
        emotion_title: str,
        generated_combined: bytes,
        reference_audio: bytes,
        emotion_audio: bytes,
    ) -> dict[str, Any]:
        """Pack raw audio payloads into an ITTS bundle and persist it."""
        generated_sha256 = self.storage.calculate_data_sha256(generated_combined)

        duplicate = await self.bundle_service.check_duplicate(generated_sha256)
        if duplicate:
            return {
                "status": "duplicate",
                "existing_bundle": BundleResponse.model_validate(duplicate),
            }

        manifest = self._create_manifest(
            title=title,
            prompt_text=prompt_text,
            reference_title=reference_title,
            emotion_title=emotion_title,
            generated_combined=generated_combined,
            reference_audio=reference_audio,
            emotion_audio=emotion_audio,
            generated_sha256=generated_sha256,
        )

        schema_path = Path(__file__).resolve().parents[2] / "docs" / "bundle.schema.json"
        validate_manifest_with_schema(manifest, schema_path, strict_schema=False)
        validate_segment_index_contract(manifest)

        itts_data = self._build_bundle_bytes(
            manifest=manifest,
            generated_combined=generated_combined,
            reference_audio=reference_audio,
            emotion_audio=emotion_audio,
        )

        filename = f"{self._safe_slug(title)}.itts"
        s3_key = await self.storage.upload_file(filename=filename, data=itts_data, prefix="bundles")

        bundle = await self.bundle_service.create_bundle(
            title=title,
            filename=filename,
            s3_key=s3_key,
            manifest_json=json.dumps(manifest, ensure_ascii=False),
            generated_audio_sha256=generated_sha256,
            reference_voice=reference_title,
            emotion_voice=emotion_title,
            mode="combined",
        )

        return {
            "status": "created",
            "bundle": bundle,
        }

    @staticmethod
    def _create_manifest(
        title: str,
        prompt_text: str,
        reference_title: str,
        emotion_title: str,
        generated_combined: bytes,
        reference_audio: bytes,
        emotion_audio: bytes,
        generated_sha256: str,
    ) -> dict[str, Any]:
        return {
            "format": "index-tts-bundle",
            "version": "1.1.0",
            "bundle_id": str(uuid.uuid4()),
            "created_at": now_utc_iso(),
            "prompt": {
                "text": prompt_text,
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
                    "bytes": len(generated_combined),
                },
            },
            "reference_audio": {
                "title": reference_title,
                "path": "audio/reference.wav",
                "mime_type": "audio/wav",
                "sha256": sha256_bytes(reference_audio),
                "bytes": len(reference_audio),
            },
            "emotion_audio": {
                "title": emotion_title,
                "path": "audio/emotion.wav",
                "mime_type": "audio/wav",
                "sha256": sha256_bytes(emotion_audio),
                "bytes": len(emotion_audio),
            },
            "generator": {
                "app": "ITTS Backend",
                "model": "unknown",
                "settings": {
                    "source": "pack_endpoint",
                },
            },
        }

    @staticmethod
    def _build_bundle_bytes(
        manifest: dict[str, Any],
        generated_combined: bytes,
        reference_audio: bytes,
        emotion_audio: bytes,
    ) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("audio/generated/combined.wav", generated_combined)
            archive.writestr("audio/reference.wav", reference_audio)
            archive.writestr("audio/emotion.wav", emotion_audio)
        return buffer.getvalue()

    @staticmethod
    def _safe_slug(title: str) -> str:
        value = re.sub(r"[^A-Za-z0-9._-]+", "_", title.strip())
        value = value.strip("._")
        return value or "bundle"
