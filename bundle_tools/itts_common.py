import datetime as _dt
import hashlib
import json
import pathlib
import re
import wave
from typing import Any, Dict, List, Tuple


_MIME_BY_EXT = {
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}


def now_utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json_compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def guess_audio_mime(path: pathlib.Path) -> str:
    mime = _MIME_BY_EXT.get(path.suffix.lower())
    if not mime:
        raise ValueError(f"Unsupported audio extension for MIME detection: {path}")
    return mime


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_audio_meta(path: pathlib.Path) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"bytes": path.stat().st_size}
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                sr = wf.getframerate()
                channels = wf.getnchannels()
                frames = wf.getnframes()
                duration_ms = (frames / float(sr)) * 1000.0 if sr > 0 else 0.0
            meta["sample_rate_hz"] = sr
            meta["channels"] = channels
            meta["duration_ms"] = round(duration_ms, 3)
        except wave.Error:
            # Some valid WAV variants (e.g. IEEE float PCM, tag=3) are not
            # supported by the stdlib wave parser. Keep minimal metadata.
            pass
    return meta


def ensure_safe_archive_path(rel_path: str) -> str:
    if not rel_path or not isinstance(rel_path, str):
        raise ValueError("Archive path must be a non-empty string")
    if "\\" in rel_path:
        raise ValueError(f"Archive path must use forward slashes: {rel_path}")
    if rel_path.startswith("/") or re.match(r"^[A-Za-z]:", rel_path):
        raise ValueError(f"Absolute/archive-root paths are not allowed: {rel_path}")
    parts = rel_path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe archive path: {rel_path}")
    return rel_path


def fallback_manifest_validate(manifest: Dict[str, Any]) -> None:
    required = {
        "format",
        "version",
        "bundle_id",
        "created_at",
        "prompt",
        "playback",
        "generated_audio",
        "reference_audio",
        "emotion_audio",
    }
    missing = [k for k in sorted(required) if k not in manifest]
    if missing:
        raise ValueError(f"Manifest missing required top-level fields: {missing}")
    if manifest.get("format") != "index-tts-bundle":
        raise ValueError("manifest.format must be 'index-tts-bundle'")
    generated = manifest.get("generated_audio") or {}
    mode = generated.get("mode")
    if mode not in {"combined", "segments", "both"}:
        raise ValueError("generated_audio.mode must be one of: combined, segments, both")
    if mode in {"combined", "both"} and "combined" not in generated:
        raise ValueError("generated_audio.combined is required for mode=combined/both")
    if mode in {"segments", "both"} and "segments" not in generated:
        raise ValueError("generated_audio.segments is required for mode=segments/both")

    playback = manifest.get("playback") or {}
    default_source = playback.get("default_source")
    fallback_order = playback.get("fallback_order")
    segment_order = playback.get("segment_order")
    if default_source not in {"combined", "segments"}:
        raise ValueError("playback.default_source must be combined or segments")
    if not isinstance(fallback_order, list) or len(fallback_order) == 0:
        raise ValueError("playback.fallback_order must be a non-empty array")
    if segment_order != "index_asc":
        raise ValueError("playback.segment_order must be index_asc")
    for src in fallback_order:
        if src not in {"combined", "segments"}:
            raise ValueError("playback.fallback_order contains invalid source")

    if mode == "combined":
        if default_source != "combined":
            raise ValueError("mode=combined requires playback.default_source=combined")
        if any(src != "combined" for src in fallback_order):
            raise ValueError("mode=combined allows only combined in playback.fallback_order")
    if mode == "segments":
        if default_source != "segments":
            raise ValueError("mode=segments requires playback.default_source=segments")
        if any(src != "segments" for src in fallback_order):
            raise ValueError("mode=segments allows only segments in playback.fallback_order")
    if mode in {"segments", "both"}:
        if generated.get("segment_index_policy") != "zero_based_contiguous":
            raise ValueError("segments mode requires generated_audio.segment_index_policy=zero_based_contiguous")
        if not isinstance(generated.get("segments_count"), int) or int(generated["segments_count"]) <= 0:
            raise ValueError("segments mode requires positive integer generated_audio.segments_count")


def validate_segment_index_contract(manifest: Dict[str, Any]) -> None:
    generated = manifest.get("generated_audio") or {}
    mode = generated.get("mode")
    if mode not in {"segments", "both"}:
        return
    segments = generated.get("segments") or []
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments must be a non-empty array when mode uses segments")
    indexes: List[int] = []
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict) or "index" not in seg:
            raise ValueError(f"segments[{i}] missing index")
        idx = int(seg["index"])
        indexes.append(idx)
    if len(set(indexes)) != len(indexes):
        raise ValueError("segment indexes must be unique")
    min_idx = min(indexes)
    max_idx = max(indexes)
    if min_idx != 0:
        raise ValueError("segment indexes must start at 0")
    expected_count = int(generated.get("segments_count", 0))
    if expected_count != len(segments):
        raise ValueError("segments_count must equal the number of segment entries")
    if max_idx != expected_count - 1:
        raise ValueError("segment indexes must be contiguous and end at segments_count - 1")


def validate_manifest_with_schema(manifest: Dict[str, Any], schema_path: pathlib.Path, strict_schema: bool = False) -> Tuple[str, str]:
    schema = load_json(schema_path)
    try:
        import jsonschema  # type: ignore
    except ImportError:
        if strict_schema:
            raise RuntimeError(
                "jsonschema package is required for strict schema validation.\n"
                "Install it with: pip install jsonschema"
            )
        fallback_manifest_validate(manifest)
        return ("fallback", "jsonschema not installed; used fallback validator")

    validator = jsonschema.Draft202012Validator(schema)
    errors: List[str] = []
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
    if errors:
        raise ValueError("Manifest does not match schema:\n" + "\n".join(errors))
    return ("jsonschema", "validated against Draft 2020-12 schema")
