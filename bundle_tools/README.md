# Bundle Tools (`bundle_tools/`)

This folder is isolated from the original API/server code and contains utilities for the `.itts` bundle format.

Current default manifest target produced by these tools is `version: 1.1.0`.

## Files

- `pack_itts.py`: build a `.itts` file (ZIP + `manifest.json`) from local audio files and metadata
- `unpack_itts.py`: validate and unpack a `.itts` file and produce `normalized.json`
- `itts_common.py`: shared helpers (hashing, schema validation, safe paths, metadata)

## Quick Start

Run from repository root:

```powershell
python bundle_tools/pack_itts.py `
  --output outputs/sample.itts `
  --prompt-text "Hello world" `
  --generated-combined outputs/spk_1757450128.wav `
  --reference-audio examples/voice_01.wav `
  --reference-title "voice_01" `
  --emotion-audio emo_ref_audio/sample1.wav `
  --emotion-title "sample1"
```

Then unpack:

```powershell
python bundle_tools/unpack_itts.py `
  --input outputs/sample.itts `
  --output-dir outputs/sample_unpacked
```

## Segment-aware packing

If you also have per-segment generated audio files, pass `--generated-segments-json`.

Example `segments.json`:

```json
[
  { "index": 0, "path": "outputs/seg0.wav", "text": "Hello there." },
  { "index": 1, "path": "outputs/seg1.wav", "text": "This is segment two." }
]
```

Command:

```powershell
python bundle_tools/pack_itts.py `
  --output outputs/sample_both.itts `
  --prompt-text "Hello there. This is segment two." `
  --generated-combined outputs/spk_1757450128.wav `
  --generated-segments-json segments.json `
  --reference-audio examples/voice_01.wav `
  --reference-title "voice_01" `
  --emotion-audio emo_ref_audio/sample1.wav `
  --emotion-title "sample1"
```

This produces `generated_audio.mode = "both"`.
It also writes:

- `playback` contract (`default_source`, `fallback_order`, `segment_order`)
- segment integrity fields (`segment_index_policy`, `segments_count`)

## Schema validation behavior

- Default: validates against `docs/bundle.schema.json`.
- If `jsonschema` package is installed, full Draft 2020-12 validation is used.
- If not installed, tools fall back to minimal built-in validation.
- Use `--strict-schema` to require `jsonschema` and fail otherwise.

Install optional validator:

```powershell
pip install jsonschema
```

## Output of `unpack_itts.py`

`unpack_itts.py` writes:

- extracted `manifest.json`
- referenced audio files under their manifest paths
- `normalized.json` with stable keys for downstream project loaders
