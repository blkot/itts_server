import argparse
import json
import pathlib
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from itts_common import (
    dump_json_compact,
    ensure_safe_archive_path,
    guess_audio_mime,
    load_json,
    now_utc_iso,
    read_audio_meta,
    sha256_file,
    validate_segment_index_contract,
    validate_manifest_with_schema,
)


def _default_schema_path() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1] / "docs" / "bundle.schema.json"


def _read_segments(path: pathlib.Path) -> List[Dict[str, Any]]:
    raw = load_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"segments JSON must be an array: {path}")
    normalized: List[Dict[str, Any]] = []
    for i, entry in enumerate(raw):
        if isinstance(entry, str):
            normalized.append({"index": i, "path": entry})
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"segments[{i}] must be object or string")
        if "path" not in entry:
            raise ValueError(f"segments[{i}] missing required key 'path'")
        item = dict(entry)
        if "index" not in item:
            item["index"] = i
        normalized.append(item)
    return sorted(normalized, key=lambda x: int(x["index"]))


def _read_prompt_segments(path: pathlib.Path) -> List[Dict[str, Any]]:
    raw = load_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"prompt segments JSON must be an array: {path}")
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            out.append({"index": i, "text": item})
            continue
        if not isinstance(item, dict):
            raise ValueError(f"prompt segments[{i}] must be object or string")
        if "index" not in item:
            item = dict(item)
            item["index"] = i
        if "text" not in item:
            raise ValueError(f"prompt segments[{i}] missing required key 'text'")
        out.append(item)
    return sorted(out, key=lambda x: int(x["index"]))


def _build_audio_asset(src: pathlib.Path, archive_path: str) -> Dict[str, Any]:
    archive_path = ensure_safe_archive_path(archive_path)
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Audio file not found: {src}")
    asset: Dict[str, Any] = {
        "path": archive_path,
        "mime_type": guess_audio_mime(src),
        "sha256": sha256_file(src),
    }
    asset.update(read_audio_meta(src))
    return asset


def _build_manifest(
    args: argparse.Namespace,
    generated_combined: Optional[pathlib.Path],
    generated_segments: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Tuple[pathlib.Path, str]]]:
    if generated_combined is None and not generated_segments:
        raise ValueError("Provide at least one generated audio source: --generated-combined or --generated-segments-json")

    prompt: Dict[str, Any] = {"text": args.prompt_text}
    if args.prompt_language:
        prompt["language"] = args.prompt_language

    prompt_segments: Optional[List[Dict[str, Any]]] = None
    if args.prompt_segments_json:
        prompt_segments = _read_prompt_segments(pathlib.Path(args.prompt_segments_json))
    elif generated_segments and all("text" in seg for seg in generated_segments):
        prompt_segments = [{"index": seg["index"], "text": seg["text"]} for seg in generated_segments]
    if prompt_segments:
        prompt["segments"] = prompt_segments

    files_to_pack: List[Tuple[pathlib.Path, str]] = []
    generated_audio: Dict[str, Any] = {}

    if generated_combined is not None:
        ext = generated_combined.suffix.lower()
        combined_archive = f"audio/generated/combined{ext}"
        generated_audio["combined"] = _build_audio_asset(generated_combined, combined_archive)
        files_to_pack.append((generated_combined, combined_archive))

    if generated_segments:
        seg_assets: List[Dict[str, Any]] = []
        seen_indexes = set()
        for seg in generated_segments:
            idx = int(seg["index"])
            if idx in seen_indexes:
                raise ValueError(f"Duplicate segment index detected: {idx}")
            seen_indexes.add(idx)
            src = pathlib.Path(seg["path"])
            ext = src.suffix.lower()
            archive_path = f"audio/generated/segments/{idx:04d}{ext}"
            asset = _build_audio_asset(src, archive_path)
            asset["index"] = idx
            for opt_key in ("text", "start_ms", "end_ms"):
                if opt_key in seg:
                    asset[opt_key] = seg[opt_key]
            seg_assets.append(asset)
            files_to_pack.append((src, archive_path))
        generated_audio["segments"] = sorted(seg_assets, key=lambda x: int(x["index"]))
        generated_audio["segment_index_policy"] = "zero_based_contiguous"
        generated_audio["segments_count"] = len(seg_assets)

    has_combined = "combined" in generated_audio
    has_segments = "segments" in generated_audio
    if has_combined and has_segments:
        generated_audio["mode"] = "both"
        playback = {
            "default_source": "combined",
            "fallback_order": ["combined", "segments"],
            "segment_order": "index_asc",
        }
    elif has_combined:
        generated_audio["mode"] = "combined"
        playback = {
            "default_source": "combined",
            "fallback_order": ["combined"],
            "segment_order": "index_asc",
        }
    else:
        generated_audio["mode"] = "segments"
        playback = {
            "default_source": "segments",
            "fallback_order": ["segments"],
            "segment_order": "index_asc",
        }

    reference_src = pathlib.Path(args.reference_audio)
    reference_archive = f"audio/reference/{reference_src.name}"
    reference_audio = _build_audio_asset(reference_src, reference_archive)
    reference_audio["title"] = args.reference_title
    files_to_pack.append((reference_src, reference_archive))

    emotion_src = pathlib.Path(args.emotion_audio)
    emotion_archive = f"audio/emotion/{emotion_src.name}"
    emotion_audio = _build_audio_asset(emotion_src, emotion_archive)
    emotion_audio["title"] = args.emotion_title
    files_to_pack.append((emotion_src, emotion_archive))

    manifest: Dict[str, Any] = {
        "format": "index-tts-bundle",
        "version": args.version,
        "bundle_id": args.bundle_id or str(uuid.uuid4()),
        "created_at": args.created_at or now_utc_iso(),
        "prompt": prompt,
        "playback": playback,
        "generated_audio": generated_audio,
        "reference_audio": reference_audio,
        "emotion_audio": emotion_audio,
        "generator": {},
    }

    if args.generator_app:
        manifest["generator"]["app"] = args.generator_app
    if args.generator_model:
        manifest["generator"]["model"] = args.generator_model
    if args.generator_settings_json:
        settings = load_json(pathlib.Path(args.generator_settings_json))
        if not isinstance(settings, dict):
            raise ValueError("generator settings JSON must be an object")
        manifest["generator"]["settings"] = settings
    if not manifest["generator"]:
        del manifest["generator"]

    validate_segment_index_contract(manifest)

    return manifest, files_to_pack


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Pack audio + metadata into .itts bundle (ZIP + manifest.json).")
    p.add_argument("--output", required=True, help="Output .itts path")
    p.add_argument("--prompt-text", required=True, help="Source prompt text")
    p.add_argument("--prompt-language", help="Optional language tag")
    p.add_argument("--prompt-segments-json", help="Optional JSON array for prompt.segments")

    p.add_argument("--generated-combined", help="Combined generated audio path (current API default output)")
    p.add_argument("--generated-segments-json", help="Optional JSON array of generated segment objects")

    p.add_argument("--reference-audio", required=True, help="Reference speaker audio path")
    p.add_argument("--reference-title", required=True, help="Reference speaker title")
    p.add_argument("--emotion-audio", required=True, help="Emotion reference audio path")
    p.add_argument("--emotion-title", required=True, help="Emotion reference title")

    p.add_argument("--version", default="1.1.0", help="Manifest semantic version")
    p.add_argument("--bundle-id", help="Override auto-generated bundle_id")
    p.add_argument("--created-at", help="Override created_at (RFC3339)")
    p.add_argument("--generator-app", default="IndexTTS2 API", help="Generator app name")
    p.add_argument("--generator-model", default="indextts2", help="Generator model name")
    p.add_argument("--generator-settings-json", help="Optional JSON object for generator.settings")

    p.add_argument("--schema", default=str(_default_schema_path()), help="Path to bundle JSON schema")
    p.add_argument("--skip-schema-validation", action="store_true", help="Skip schema validation")
    p.add_argument("--strict-schema", action="store_true", help="Require jsonschema package for full validation")
    p.add_argument(
        "--compression",
        choices=("stored", "deflated"),
        default="deflated",
        help="ZIP compression mode",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()

    output_path = pathlib.Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generated_combined = pathlib.Path(args.generated_combined) if args.generated_combined else None
    generated_segments: List[Dict[str, Any]] = []
    if args.generated_segments_json:
        generated_segments = _read_segments(pathlib.Path(args.generated_segments_json))

    manifest, files_to_pack = _build_manifest(args, generated_combined, generated_segments)

    if not args.skip_schema_validation:
        engine, detail = validate_manifest_with_schema(manifest, pathlib.Path(args.schema), strict_schema=args.strict_schema)
        print(f"[INFO] Schema validation: {engine} ({detail})")
    else:
        print("[INFO] Schema validation skipped")

    compression = zipfile.ZIP_STORED if args.compression == "stored" else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(output_path, "w", compression=compression) as zf:
        zf.writestr("manifest.json", dump_json_compact(manifest))
        for src, archive_rel in files_to_pack:
            zf.write(src, arcname=archive_rel)

    print(f"[OK] Bundle written: {output_path}")
    print(f"[OK] Generated mode: {manifest['generated_audio']['mode']}")
    print(f"[OK] Bundle id: {manifest['bundle_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
