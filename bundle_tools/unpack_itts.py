import argparse
import json
import pathlib
import zipfile
from typing import Any, Dict, List, Tuple

from itts_common import (
    dump_json_compact,
    ensure_safe_archive_path,
    sha256_bytes,
    validate_segment_index_contract,
    validate_manifest_with_schema,
)


def _default_schema_path() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1] / "docs" / "bundle.schema.json"


def _collect_declared_assets(manifest: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    out: List[Tuple[str, Dict[str, Any]]] = []
    gen = manifest["generated_audio"]
    if "combined" in gen:
        out.append(("generated_audio.combined", gen["combined"]))
    for seg in gen.get("segments", []):
        out.append((f"generated_audio.segments[{seg.get('index', '?')}]", seg))
    out.append(("reference_audio", manifest["reference_audio"]))
    out.append(("emotion_audio", manifest["emotion_audio"]))
    return out


def _safe_write_file(root: pathlib.Path, rel_path: str, data: bytes) -> pathlib.Path:
    rel_path = ensure_safe_archive_path(rel_path)
    target = (root / rel_path).resolve()
    root_resolved = root.resolve()
    if root_resolved not in target.parents and target != root_resolved:
        raise ValueError(f"Path escapes output directory: {rel_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def _build_normalized(manifest: Dict[str, Any], output_dir: pathlib.Path) -> Dict[str, Any]:
    gen = manifest["generated_audio"]
    normalized: Dict[str, Any] = {
        "bundle_id": manifest["bundle_id"],
        "version": manifest["version"],
        "created_at": manifest["created_at"],
        "prompt_text": manifest["prompt"]["text"],
        "generated_mode": gen["mode"],
        "generated_combined_path": None,
        "generated_segments": [],
        "reference": {
            "title": manifest["reference_audio"]["title"],
            "path": str((output_dir / manifest["reference_audio"]["path"]).resolve()),
            "mime_type": manifest["reference_audio"]["mime_type"],
        },
        "emotion": {
            "title": manifest["emotion_audio"]["title"],
            "path": str((output_dir / manifest["emotion_audio"]["path"]).resolve()),
            "mime_type": manifest["emotion_audio"]["mime_type"],
        },
    }
    if "combined" in gen:
        normalized["generated_combined_path"] = str((output_dir / gen["combined"]["path"]).resolve())
    for seg in gen.get("segments", []):
        normalized["generated_segments"].append(
            {
                "index": seg["index"],
                "text": seg.get("text"),
                "path": str((output_dir / seg["path"]).resolve()),
                "mime_type": seg["mime_type"],
                "start_ms": seg.get("start_ms"),
                "end_ms": seg.get("end_ms"),
            }
        )
    normalized["generated_segments"].sort(key=lambda x: x["index"])
    return normalized


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Unpack and validate an .itts bundle.")
    p.add_argument("--input", required=True, help="Input .itts bundle path")
    p.add_argument("--output-dir", required=True, help="Extraction directory")
    p.add_argument("--schema", default=str(_default_schema_path()), help="Path to bundle JSON schema")
    p.add_argument("--skip-schema-validation", action="store_true", help="Skip schema validation")
    p.add_argument("--strict-schema", action="store_true", help="Require jsonschema package for full validation")
    p.add_argument("--skip-hash-check", action="store_true", help="Skip SHA-256 integrity checks")
    p.add_argument(
        "--normalized-json",
        help="Write normalized loader-friendly JSON (default: <output-dir>/normalized.json)",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()

    input_path = pathlib.Path(args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Bundle not found: {input_path}")
    output_dir = pathlib.Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(input_path, "r") as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            raise ValueError("Bundle missing manifest.json")
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))

        if not args.skip_schema_validation:
            engine, detail = validate_manifest_with_schema(
                manifest,
                pathlib.Path(args.schema),
                strict_schema=args.strict_schema,
            )
            print(f"[INFO] Schema validation: {engine} ({detail})")
        else:
            print("[INFO] Schema validation skipped")
        validate_segment_index_contract(manifest)

        declared_assets = _collect_declared_assets(manifest)
        # Always extract manifest.
        _safe_write_file(output_dir, "manifest.json", zf.read("manifest.json"))

        for label, asset in declared_assets:
            rel = ensure_safe_archive_path(asset["path"])
            if rel not in names:
                raise ValueError(f"Declared asset missing in archive: {label} -> {rel}")
            data = zf.read(rel)
            if (not args.skip_hash_check) and asset.get("sha256"):
                digest = sha256_bytes(data)
                if digest.lower() != str(asset["sha256"]).lower():
                    raise ValueError(f"SHA256 mismatch for {label}: expected {asset['sha256']}, got {digest}")
            _safe_write_file(output_dir, rel, data)

    normalized = _build_normalized(manifest, output_dir)
    normalized_path = pathlib.Path(args.normalized_json).resolve() if args.normalized_json else (output_dir / "normalized.json")
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(dump_json_compact(normalized), encoding="utf-8")

    print(f"[OK] Bundle unpacked: {input_path}")
    print(f"[OK] Extracted to: {output_dir}")
    print(f"[OK] Normalized JSON: {normalized_path}")
    print(f"[OK] Generated mode: {manifest['generated_audio']['mode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
