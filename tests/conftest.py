import io
import json
import math
import pathlib
import sys
import wave
import zipfile
from dataclasses import dataclass

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import Base
from bundle_tools.itts_common import now_utc_iso, sha256_bytes


@pytest_asyncio.fixture
async def db_session(tmp_path) -> AsyncSession:
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@dataclass
class SampleIttsBundle:
    filename: str
    bundle_id: str
    reference_title: str
    emotion_title: str
    prompt_text: str
    segment_texts: list[str]
    data: bytes
    generated_audio: bytes
    reference_audio: bytes
    emotion_audio: bytes


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class FakeMinio:
    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, bucket: str, key: str, data, length: int):
        payload = data.read(length)
        self._objects[(bucket, key)] = payload

    def get_object(self, bucket: str, key: str) -> FakeResponse:
        return FakeResponse(self._objects[(bucket, key)])

    def remove_object(self, bucket: str, key: str) -> None:
        self._objects.pop((bucket, key), None)

    def stat_object(self, bucket: str, key: str) -> dict:
        if (bucket, key) not in self._objects:
            raise KeyError(key)
        return {"size": len(self._objects[(bucket, key)])}


def _build_wav_bytes(duration_ms: int, frequency_hz: int, sample_rate: int = 16000) -> bytes:
    frame_count = int(sample_rate * duration_ms / 1000)
    amplitude = 12000
    pcm = bytearray()

    for index in range(frame_count):
        sample = int(amplitude * math.sin(2 * math.pi * frequency_hz * (index / sample_rate)))
        pcm.extend(sample.to_bytes(2, byteorder="little", signed=True))

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(pcm))
    return output.getvalue()


def _build_sample_itts_bundle(
    bundle_id: str,
    reference_title: str,
    emotion_title: str,
    segment_texts: list[str],
    durations_ms: list[int],
    frequencies_hz: list[int],
) -> SampleIttsBundle:
    prompt_segments: list[dict[str, int | str]] = []
    combined_pcm = bytearray()
    start_ms = 0

    for text, duration_ms, frequency_hz in zip(segment_texts, durations_ms, frequencies_hz, strict=True):
        segment_wav = _build_wav_bytes(duration_ms=duration_ms, frequency_hz=frequency_hz)
        with wave.open(io.BytesIO(segment_wav), "rb") as segment_reader:
            combined_pcm.extend(segment_reader.readframes(segment_reader.getnframes()))

        end_ms = start_ms + duration_ms
        prompt_segments.append(
            {
                "index": len(prompt_segments),
                "text": text,
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
        )
        start_ms = end_ms

    combined_output = io.BytesIO()
    with wave.open(combined_output, "wb") as combined_wav:
        combined_wav.setnchannels(1)
        combined_wav.setsampwidth(2)
        combined_wav.setframerate(16000)
        combined_wav.writeframes(bytes(combined_pcm))
    generated_audio = combined_output.getvalue()

    reference_audio = _build_wav_bytes(duration_ms=200, frequency_hz=330)
    emotion_audio = _build_wav_bytes(duration_ms=200, frequency_hz=550)
    prompt_text = " ".join(segment_texts)

    manifest = {
        "format": "index-tts-bundle",
        "version": "1.1.0",
        "bundle_id": bundle_id,
        "created_at": now_utc_iso(),
        "prompt": {
            "text": prompt_text,
            "segments": prompt_segments,
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
                "sha256": sha256_bytes(generated_audio),
                "bytes": len(generated_audio),
                "duration_ms": sum(durations_ms),
                "sample_rate_hz": 16000,
                "channels": 1,
            },
        },
        "reference_audio": {
            "title": reference_title,
            "path": "audio/reference.wav",
            "mime_type": "audio/wav",
            "sha256": sha256_bytes(reference_audio),
            "bytes": len(reference_audio),
            "duration_ms": 200,
            "sample_rate_hz": 16000,
            "channels": 1,
        },
        "emotion_audio": {
            "title": emotion_title,
            "path": "audio/emotion.wav",
            "mime_type": "audio/wav",
            "sha256": sha256_bytes(emotion_audio),
            "bytes": len(emotion_audio),
            "duration_ms": 200,
            "sample_rate_hz": 16000,
            "channels": 1,
        },
        "generator": {
            "app": "pytest",
            "model": "fixture-generator",
            "settings": {
                "source": "tests",
            },
        },
    }

    bundle_bytes = io.BytesIO()
    with zipfile.ZipFile(bundle_bytes, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("audio/generated/combined.wav", generated_audio)
        archive.writestr("audio/reference.wav", reference_audio)
        archive.writestr("audio/emotion.wav", emotion_audio)

    return SampleIttsBundle(
        filename=f"{bundle_id}.itts",
        bundle_id=bundle_id,
        reference_title=reference_title,
        emotion_title=emotion_title,
        prompt_text=prompt_text,
        segment_texts=segment_texts,
        data=bundle_bytes.getvalue(),
        generated_audio=generated_audio,
        reference_audio=reference_audio,
        emotion_audio=emotion_audio,
    )


@pytest.fixture
def fake_minio() -> FakeMinio:
    return FakeMinio()


@pytest.fixture
def sample_itts_bundle() -> SampleIttsBundle:
    return _build_sample_itts_bundle(
        bundle_id="sample-bundle-one",
        reference_title="ref-alpha",
        emotion_title="sample1",
        segment_texts=["alpha segment", "beta segment"],
        durations_ms=[320, 360],
        frequencies_hz=[440, 660],
    )


@pytest.fixture
def alt_sample_itts_bundle() -> SampleIttsBundle:
    return _build_sample_itts_bundle(
        bundle_id="sample-bundle-two",
        reference_title="ref-alpha",
        emotion_title="sample1",
        segment_texts=["gamma segment", "delta segment"],
        durations_ms=[280, 420],
        frequencies_hz=[520, 740],
    )
