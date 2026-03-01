import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Bundle, Playlist, PlaylistEntry, Segment
from app.models.schemas import BundleResponse, SegmentResponse
from bundle_tools.itts_common import (
    ensure_safe_archive_path,
    validate_manifest_with_schema,
    validate_segment_index_contract,
)


class BundleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_duplicate(self, sha256: str) -> Optional[Bundle]:
        """Check if a bundle with the same generated audio hash already exists."""
        result = await self.db.execute(
            select(Bundle).where(Bundle.generated_audio_sha256 == sha256)
        )
        return result.scalar_one_or_none()

    async def create_bundle(
        self,
        title: str,
        filename: str,
        s3_key: str,
        manifest_json: str,
        generated_audio_sha256: Optional[str] = None,
        reference_voice: Optional[str] = None,
        emotion_voice: Optional[str] = None,
        mode: Optional[str] = None,
        total_duration_ms: Optional[int] = None,
        is_concatenated: bool = False,
        source_bundle_ids: Optional[str] = None,
    ) -> BundleResponse:
        """Create a bundle, attach segments, and maintain auto-playlists in one transaction."""
        bundle = Bundle(
            title=title,
            filename=filename,
            s3_key=s3_key,
            manifest_json=manifest_json,
            generated_audio_sha256=generated_audio_sha256,
            reference_voice=reference_voice,
            emotion_voice=emotion_voice,
            mode=mode,
            total_duration_ms=total_duration_ms,
            is_concatenated=is_concatenated,
            source_bundle_ids=source_bundle_ids,
        )
        self.db.add(bundle)
        await self.db.flush()

        manifest = self._safe_load_manifest_json(manifest_json)
        await self._create_segments_from_manifest(bundle.id, manifest)

        await self._create_auto_playlists(bundle)
        await self._add_to_main_playlist(bundle.id)

        await self.db.commit()
        await self.db.refresh(bundle)
        return self._bundle_to_response(bundle)

    async def get_bundle(self, bundle_id: int) -> Optional[BundleResponse]:
        """Get bundle metadata by ID."""
        bundle = await self.db.get(Bundle, bundle_id)
        if not bundle:
            return None
        return self._bundle_to_response(bundle)

    async def list_bundles(self, page: int = 1, page_size: int = 50) -> list[BundleResponse]:
        """List bundles in reverse creation order with pagination."""
        safe_page = max(page, 1)
        safe_page_size = max(page_size, 1)
        offset = (safe_page - 1) * safe_page_size

        result = await self.db.execute(
            select(Bundle)
            .order_by(Bundle.created_at.desc())
            .offset(offset)
            .limit(safe_page_size)
        )
        bundles = result.scalars().all()
        return [self._bundle_to_response(bundle) for bundle in bundles]

    async def delete_bundle(self, bundle_id: int) -> bool:
        """Delete a bundle by ID."""
        bundle = await self.db.get(Bundle, bundle_id)
        if not bundle:
            return False

        await self.db.delete(bundle)
        await self.db.commit()
        return True

    async def get_segments(self, bundle_id: int) -> list[SegmentResponse]:
        """Get ordered prompt segments for a bundle."""
        result = await self.db.execute(
            select(Segment)
            .where(Segment.bundle_id == bundle_id)
            .order_by(Segment.segment_index.asc())
        )
        segments = result.scalars().all()
        return [
            SegmentResponse(
                id=segment.id,
                segment_index=segment.segment_index,
                text_prompt=segment.text_prompt,
                normalized_text=segment.normalized_text,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
            )
            for segment in segments
        ]

    async def _create_auto_playlists(self, bundle: Bundle) -> None:
        """Create and attach reference/emotion auto-playlists."""
        if bundle.reference_voice:
            await self._get_or_create_playlist(
                name=bundle.reference_voice,
                is_auto_generated=True,
                auto_type="reference",
                auto_value=bundle.reference_voice,
            )
            await self._add_to_playlist(bundle.id, bundle.reference_voice)

        if bundle.emotion_voice:
            await self._get_or_create_playlist(
                name=bundle.emotion_voice,
                is_auto_generated=True,
                auto_type="emotion",
                auto_value=bundle.emotion_voice,
            )
            await self._add_to_playlist(bundle.id, bundle.emotion_voice)

    async def _add_to_main_playlist(self, bundle_id: int) -> None:
        await self._get_or_create_playlist(name="Main", is_auto_generated=True)
        await self._add_to_playlist(bundle_id, "Main")

    async def _get_or_create_playlist(
        self,
        name: str,
        is_auto_generated: bool,
        auto_type: Optional[str] = None,
        auto_value: Optional[str] = None,
    ) -> Playlist:
        result = await self.db.execute(select(Playlist).where(Playlist.name == name))
        playlist = result.scalar_one_or_none()
        if playlist:
            return playlist

        playlist = Playlist(
            name=name,
            is_auto_generated=is_auto_generated,
            auto_type=auto_type,
            auto_value=auto_value,
        )
        self.db.add(playlist)
        await self.db.flush()
        return playlist

    async def _add_to_playlist(self, bundle_id: int, playlist_name: str) -> None:
        result = await self.db.execute(select(Playlist).where(Playlist.name == playlist_name))
        playlist = result.scalar_one_or_none()
        if not playlist:
            return

        entry_result = await self.db.execute(
            select(PlaylistEntry).where(
                PlaylistEntry.playlist_id == playlist.id,
                PlaylistEntry.bundle_id == bundle_id,
            )
        )
        existing = entry_result.scalar_one_or_none()
        if existing:
            return

        self.db.add(PlaylistEntry(playlist_id=playlist.id, bundle_id=bundle_id))

    async def _create_segments_from_manifest(self, bundle_id: int, manifest: dict[str, Any]) -> None:
        prompt = manifest.get("prompt") or {}
        prompt_segments = prompt.get("segments") or []
        generated_audio = manifest.get("generated_audio") or {}
        generated_segments_raw = generated_audio.get("segments") or []

        generated_by_index: dict[int, dict[str, Any]] = {}
        for generated in generated_segments_raw:
            if not isinstance(generated, dict):
                continue
            if "index" not in generated:
                continue
            try:
                idx = int(generated["index"])
            except (TypeError, ValueError):
                continue
            generated_by_index[idx] = generated

        for segment in prompt_segments:
            if not isinstance(segment, dict):
                continue
            if "index" not in segment or "text" not in segment:
                continue
            try:
                idx = int(segment["index"])
            except (TypeError, ValueError):
                continue

            generated = generated_by_index.get(idx, {})
            self.db.add(
                Segment(
                    bundle_id=bundle_id,
                    segment_index=idx,
                    text_prompt=str(segment.get("text", "")),
                    normalized_text=self._optional_str(segment.get("normalized_text")),
                    start_ms=self._optional_int(segment.get("start_ms")),
                    end_ms=self._optional_int(segment.get("end_ms")),
                    filename=self._optional_str(generated.get("path")),
                    sha256=self._optional_str(generated.get("sha256")),
                )
            )

    @staticmethod
    def extract_manifest_from_itts(itts_data: bytes) -> dict[str, Any]:
        """Extract and validate manifest.json from an ITTS bundle."""
        with zipfile.ZipFile(io.BytesIO(itts_data)) as archive:
            try:
                manifest_bytes = archive.read("manifest.json")
            except KeyError as exc:
                raise ValueError("manifest.json not found in ITTS bundle") from exc

        try:
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("manifest.json is not valid UTF-8 JSON") from exc

        if not isinstance(manifest, dict):
            raise ValueError("manifest.json must be a JSON object")

        BundleService._apply_v1_playback_fallback(manifest)

        schema_path = Path(__file__).resolve().parents[2] / "docs" / "bundle.schema.json"
        validate_manifest_with_schema(manifest, schema_path, strict_schema=False)
        validate_segment_index_contract(manifest)
        return manifest

    @staticmethod
    def extract_file_from_itts(itts_data: bytes, path: str) -> bytes:
        """Extract a single safe relative path from an ITTS archive."""
        safe_path = ensure_safe_archive_path(path)
        with zipfile.ZipFile(io.BytesIO(itts_data)) as archive:
            try:
                return archive.read(safe_path)
            except KeyError as exc:
                raise ValueError(f"File not found in ITTS bundle: {safe_path}") from exc

    @staticmethod
    def _apply_v1_playback_fallback(manifest: dict[str, Any]) -> None:
        playback = manifest.get("playback")
        if playback:
            return

        mode = ((manifest.get("generated_audio") or {}).get("mode") or "combined").lower()
        if mode == "segments":
            default_source = "segments"
            fallback_order = ["segments"]
        elif mode == "both":
            default_source = "combined"
            fallback_order = ["combined", "segments"]
        else:
            default_source = "combined"
            fallback_order = ["combined"]

        manifest["playback"] = {
            "default_source": default_source,
            "fallback_order": fallback_order,
            "segment_order": "index_asc",
        }

    @staticmethod
    def _safe_load_manifest_json(manifest_json: str) -> dict[str, Any]:
        try:
            manifest = json.loads(manifest_json)
        except json.JSONDecodeError:
            return {}
        if isinstance(manifest, dict):
            return manifest
        return {}

    @staticmethod
    def _bundle_to_response(bundle: Bundle) -> BundleResponse:
        return BundleResponse(
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
            created_at=BundleService._datetime_to_utc_string(bundle.created_at),
        )

    @staticmethod
    def _datetime_to_utc_string(value: datetime) -> str:
        if value.tzinfo is None:
            dt = value.replace(tzinfo=timezone.utc)
        else:
            dt = value.astimezone(timezone.utc)
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _optional_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value)
        return text if text else None
