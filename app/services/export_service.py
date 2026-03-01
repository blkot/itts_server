import io
import json
import wave
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Bundle, Export, Job
from app.services.bundle_service import BundleService
from app.services.storage_service import StorageService


class ExportService:
    def __init__(self, db: AsyncSession, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.bundle_service = BundleService(db)

    async def create_export_job(
        self,
        bundle_id: int,
        segment_indices: list[int],
        silence_ms: int = 100,
    ) -> int:
        """Create an async export job and return its identifier."""
        job = Job(
            type="export",
            status="pending",
            input_params=json.dumps(
                {
                    "bundle_id": bundle_id,
                    "segment_indices": segment_indices,
                    "silence_ms": silence_ms,
                }
            ),
            progress=0.0,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job.id

    async def process_export_job(self, job_id: int) -> Optional[int]:
        """Process an export job and return the export record id."""
        job = await self.db.get(Job, job_id)
        if job is None:
            return None

        try:
            job.status = "processing"
            job.progress = 0.1
            await self.db.commit()

            params = json.loads(job.input_params)
            bundle_id = int(params["bundle_id"])
            segment_indices = [int(index) for index in params.get("segment_indices", [])]
            silence_ms = int(params.get("silence_ms", 100))

            bundle = await self.db.get(Bundle, bundle_id)
            if bundle is None:
                raise ValueError("Bundle not found")

            itts_data = await self.storage.download_file(bundle.s3_key)
            segments = self._extract_segments_from_itts(itts_data, segment_indices)
            joined_audio = await self.join_segments(segments, silence_ms=silence_ms)

            export_filename = f"export_{bundle_id}_{job_id}.wav"
            s3_key = await self.storage.upload_file(export_filename, joined_audio, prefix="exports")

            export = Export(
                bundle_id=bundle_id,
                s3_key=s3_key,
                segment_indices=json.dumps(segment_indices),
                join_silence_ms=silence_ms,
            )
            self.db.add(export)
            await self.db.commit()
            await self.db.refresh(export)

            job.status = "completed"
            job.progress = 1.0
            job.result_export_id = export.id
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

            return export.id
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise

    async def join_segments(self, segments: list[Any], silence_ms: int = 100) -> bytes:
        """Join WAV segment payloads with optional silence between segments."""
        normalized_segments = await self._resolve_segments(segments)
        if not normalized_segments:
            raise ValueError("No segments to join")

        first_data, _, _ = normalized_segments[0]
        with wave.open(io.BytesIO(first_data), "rb") as first_wav:
            sample_rate = first_wav.getframerate()
            channels = first_wav.getnchannels()
            sampwidth = first_wav.getsampwidth()

        silence_samples = int((max(silence_ms, 0) / 1000.0) * sample_rate)
        silence_frame = b"\x00" * silence_samples * channels * sampwidth

        output = io.BytesIO()
        with wave.open(output, "wb") as out_wav:
            out_wav.setnchannels(channels)
            out_wav.setsampwidth(sampwidth)
            out_wav.setframerate(sample_rate)

            for index, (segment_data, _, _) in enumerate(normalized_segments):
                with wave.open(io.BytesIO(segment_data), "rb") as segment_wav:
                    out_wav.writeframes(segment_wav.readframes(segment_wav.getnframes()))

                if index < len(normalized_segments) - 1 and silence_samples > 0:
                    out_wav.writeframes(silence_frame)

        return output.getvalue()

    def _extract_segments_from_itts(
        self,
        itts_data: bytes,
        segment_indices: list[int],
    ) -> list[tuple[bytes, int, Optional[int]]]:
        """Extract selected segments from an ITTS bundle."""
        manifest = BundleService.extract_manifest_from_itts(itts_data)
        generated = manifest.get("generated_audio") or {}

        selected = set(segment_indices)
        segments: list[tuple[bytes, int, Optional[int]]] = []

        mode = generated.get("mode")
        if mode in {"segments", "both"} and generated.get("segments"):
            for seg in generated.get("segments", []):
                seg_index = int(seg.get("index", -1))
                if seg_index not in selected:
                    continue
                segment_data = BundleService.extract_file_from_itts(itts_data, str(seg["path"]))
                segments.append(
                    (
                        segment_data,
                        self._to_int(seg.get("start_ms"), default=0),
                        self._to_int(seg.get("end_ms"), default=None),
                    )
                )
            if segments:
                return segments

        combined = generated.get("combined") or {}
        combined_path = combined.get("path")
        if not isinstance(combined_path, str):
            return []

        combined_data = BundleService.extract_file_from_itts(itts_data, combined_path)
        prompt_segments = (manifest.get("prompt") or {}).get("segments") or []

        for segment in prompt_segments:
            idx = self._to_int(segment.get("index"), default=-1)
            if idx not in selected:
                continue
            start_ms = self._to_int(segment.get("start_ms"), default=0)
            end_ms = self._to_int(segment.get("end_ms"), default=None)
            segment_data = self._extract_wav_segment(combined_data, start_ms=start_ms, end_ms=end_ms)
            segments.append((segment_data, start_ms, end_ms))

        return segments

    def _extract_wav_segment(self, wav_data: bytes, start_ms: int, end_ms: Optional[int]) -> bytes:
        """Extract a sub-range from a WAV payload and return WAV bytes."""
        with wave.open(io.BytesIO(wav_data), "rb") as source:
            sample_rate = source.getframerate()
            channels = source.getnchannels()
            sampwidth = source.getsampwidth()
            total_frames = source.getnframes()

            start_frame = int((max(start_ms, 0) / 1000.0) * sample_rate)
            end_frame = (
                int((end_ms / 1000.0) * sample_rate)
                if end_ms is not None
                else total_frames
            )
            start_frame = min(max(start_frame, 0), total_frames)
            end_frame = min(max(end_frame, start_frame), total_frames)

            source.setpos(start_frame)
            frames = source.readframes(end_frame - start_frame)

        out = io.BytesIO()
        with wave.open(out, "wb") as target:
            target.setnchannels(channels)
            target.setsampwidth(sampwidth)
            target.setframerate(sample_rate)
            target.writeframes(frames)
        return out.getvalue()

    async def _resolve_segments(
        self,
        segments: list[Any],
    ) -> list[tuple[bytes, int, Optional[int]]]:
        resolved: list[tuple[bytes, int, Optional[int]]] = []
        for seg in segments:
            if isinstance(seg, tuple) and len(seg) == 3:
                data = seg[0]
                if isinstance(data, (bytes, bytearray)):
                    resolved.append((bytes(data), self._to_int(seg[1], 0), self._to_int(seg[2], None)))
                    continue

            s3_key = getattr(seg, "s3_key", None)
            if isinstance(s3_key, str) and s3_key:
                data = await self.storage.download_file(s3_key)
                resolved.append(
                    (
                        data,
                        self._to_int(getattr(seg, "start_ms", 0), default=0),
                        self._to_int(getattr(seg, "end_ms", None), default=None),
                    )
                )

        return resolved

    @staticmethod
    def _to_int(value: Any, default: Optional[int]) -> Optional[int]:
        if value is None:
            return default
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return default
