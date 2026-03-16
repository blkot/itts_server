# Audio Asset Extraction & Playback Optimization Design

**Date:** 2026-03-16
**Project:** ITTS Backend
**Purpose:** Optimize audio playback by extracting ITTS audio files after upload and serving them directly, eliminating slow ZIP unpacking on every request.

---

## Overview

Transform audio playback from "slow ZIP extraction" to "instant file serving" by extracting audio files from ITTS bundles after upload and storing them as deduplicated assets in MinIO. This eliminates the performance bottleneck of unpacking ZIP files on every audio request while maintaining efficient storage through SHA-256 deduplication of shared voice audio.

**Problem:** Currently, playing audio from an ITTS bundle requires downloading the ZIP file and extracting the desired audio file every time, which is slow.

**Solution:** Extract all audio files to MinIO immediately after upload, serve them directly for playback, and deduplicate shared audio files (reference/emotion voices) across bundles.

**Key Insights from Requirements:**
- Multiple ITTS bundles often share the same reference/emotion voice audio
- Deduplication by SHA-256 hash saves significant storage
- Background extraction is acceptable (audio files aren't too large)
- Frontend becomes simpler: direct playback instead of export + poll + download
- Keep original ITTS files for backup/archive
- Handle partial extraction failures gracefully

---

## Architecture

### Current Flow (Slow)

```
User: Play segment 3
  ↓
Frontend: Request audio
  ↓
Backend: Download ITTS from MinIO
  ↓
Backend: Extract ZIP (slow!)
  ↓
Backend: Extract segment 3
  ↓
Backend: Serve audio file
```

### Optimized Flow (Fast)

```
User: Upload ITTS
  ↓
Backend: Create bundle (fast)
  ↓
Background: Extract all audio files
  ↓
MinIO: Store extracted audio (deduplicated)
  ↓
Database: Link audio assets to bundle
  ↓
User: Play segment 3
  ↓
Frontend: Request audio
  ↓
Backend: Serve from MinIO directly (instant!)
```

---

## Database Schema

### New Table: `audio_assets`

Stores metadata for each extracted audio file with SHA-256 deduplication.

```sql
CREATE TABLE audio_assets (
    id INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,          -- SHA-256 hash for deduplication
    title TEXT NOT NULL,                   -- Friendly filename from manifest
    source_type TEXT NOT NULL,             -- 'reference_voice', 'emotion_voice', 'generated', 'combined'
    original_filename TEXT,                -- Original path in ITTS (e.g., 'generated/audio_0.wav')
    content_type TEXT NOT NULL,            -- 'audio/wav'
    file_size_bytes INTEGER,               -- File size for stats
    minio_key TEXT NOT NULL UNIQUE,        -- Storage path: 'audio/assets/{bundle_id}/{source_type}/{title}.wav'
    bundle_id INTEGER NOT NULL,            -- Original bundle this was first extracted from
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (bundle_id) REFERENCES bundles(id) ON DELETE CASCADE
);

CREATE INDEX idx_audio_assets_sha256 ON audio_assets(sha256);
CREATE INDEX idx_audio_assets_bundle_id ON audio_assets(bundle_id);
```

**Fields:**
- `id`: Primary key
- `sha256`: SHA-256 hash of audio file (UNIQUE - enables deduplication)
- `title`: Friendly filename (e.g., "audio_0", "reference", "emotion")
- `source_type`: Audio category from ITTS structure
- `original_filename`: Full path from manifest (e.g., "generated/audio_0.wav")
- `content_type`: MIME type ("audio/wav")
- `file_size_bytes`: File size
- `minio_key`: Storage path in MinIO
- `bundle_id`: First bundle that extracted this file
- `created_at`: Timestamp

### New Table: `bundle_audio_assets`

Junction table for many-to-many relationship between bundles and audio assets.

```sql
CREATE TABLE bundle_audio_assets (
    id INTEGER PRIMARY KEY,
    bundle_id INTEGER NOT NULL,
    audio_asset_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,             -- 'reference_voice', 'emotion_voice', 'generated', 'combined'
    FOREIGN KEY (bundle_id) REFERENCES bundles(id) ON DELETE CASCADE,
    FOREIGN KEY (audio_asset_id) REFERENCES audio_assets(id) ON DELETE CASCADE,
    UNIQUE(bundle_id, audio_asset_id)
);

CREATE INDEX idx_bundle_audio_assets_bundle_id ON bundle_audio_assets(bundle_id);
CREATE INDEX idx_bundle_audio_assets_audio_asset_id ON bundle_audio_assets(audio_asset_id);
```

**Purpose:** Multiple bundles can share the same audio asset (e.g., same reference voice). The junction table tracks which audio assets belong to which bundles.

### Additions to `bundles` Table

```sql
ALTER TABLE bundles ADD COLUMN audio_extraction_status TEXT DEFAULT 'not_extracted';
ALTER TABLE bundles ADD COLUMN extraction_job_id INTEGER;
ALTER TABLE bundles ADD COLUMN extraction_error_message TEXT;
```

**New Fields:**
- `audio_extraction_status`: "not_extracted", "extracting", "completed", "partial_failure", "failed"
- `extraction_job_id`: Link to extraction job
- `extraction_error_message`: Error details if extraction fails

---

## MinIO Storage Structure

### Original ITTS Files
```
bundles/
  └── {uuid}.itts              # Original ITTS (ZIP archive)
```

### Extracted Audio Files
```
audio/
  └── assets/
      └── {bundle_id}/
          ├── reference_voice/
          │   └── {title}.wav
          ├── emotion_voice/
          │   └── {title}.wav
          ├── generated/
          │   ├── audio_0.wav
          │   ├── audio_1.wav
          │   └── ...
          └── combined.wav (if exists)
```

**Example:**
```
audio/assets/1/reference_voice/reference.wav
audio/assets/1/emotion_voice/emotion.wav
audio/assets/1/generated/audio_0.wav
audio/assets/1/generated/audio_1.wav
audio/assets/1/generated/audio_2.wav
audio/assets/1/combined.wav
```

**Deduplication:** Shared audio files keep their original path from the first bundle that extracted them.

---

## Extraction Job Flow

### 1. Initial Upload Flow

```
User uploads ITTS (POST /api/bundles)
  ↓
Backend receives ITTS data
  ↓
1. Calculate SHA-256 of combined.wav (if exists)
  ↓
2. Check for duplicate bundle
  ↓
3. Create bundle record (status='not_extracted')
  ↓
4. Create extraction job in job_store
  ↓
5. Update bundle.extraction_job_id
  ↓
6. Update bundle.audio_extraction_status = 'extracting'
  ↓
7. Return bundle_id + job_id immediately (fast response!)
  ↓
Background: ExtractionJobService runs
  ├─ Download ITTS from MinIO
  ├─ Unpack ZIP archive
  ├─ For each audio file:
  │   ├─ Read file data
  │   ├─ Calculate SHA-256
  │   ├─ Check if audio_asset exists with this SHA256
  │   ├─ If exists: Reuse existing audio_asset record
  │   └─ If new: Create audio_asset record + upload to MinIO
  ├─ Create bundle_audio_assets records
  ├─ Update bundle.audio_extraction_status = 'completed'
  └─ Mark job as 'completed'
```

### 2. Duplicate Upload Flow (Same ITTS, New Bundle)

```
User uploads same ITTS again (SHA-256 match)
  ↓
Duplicate bundle detected
  ↓
Check extraction_job_id from existing bundle
  ↓
If extraction_job_id exists AND status='completed':
  └─ Reuse existing audio assets
      ├─ Create new bundle record
      ├─ Link to existing bundle_audio_assets
      └─ Return bundle_id immediately (no extraction needed)
  ↓
If extraction_job_id exists AND status='extracting':
  └─ Queue bundle creation
      ├─ New bundle record created
      ├─ Waits for extraction to complete
      └─ Auto-links when extraction finishes
  ↓
If no job_id or job failed:
  └─ Create new extraction job
      └─ Extract again (idempotent operation)
```

### 3. Concurrent Upload Handling

```
Two users upload same ITTS simultaneously
  ↓
First upload creates extraction_job
  ↓
Second upload checks for extraction_job_id
  ↓
Job exists and status='extracting'
  ↓
Second upload:
  ├─ Creates bundle record
  ├─ Sets extraction_job_id (same as first)
  └─ Returns immediately
  ↓
Background: Extraction completes once
  ↓
Both bundles auto-link to same audio assets
```

---

## Partial Failure Handling

### What Happens When Extraction Fails

```
Extraction in progress
  ↓
File 1 (reference_voice/reference.wav): Extracted ✓
  ├─ SHA-256 calculated
  ├─ Check audio_assets table
  ├─ Not found → Create audio_asset
  ├─ Upload to MinIO ✓
  └─ Success
  ↓
File 2 (emotion_voice/emotion.wav): Extracted ✓
  └─ ... Success
  ↓
File 3 (generated/audio_0.wav): Extracted ✓
  └─ ... Success
  ↓
File 4 (generated/audio_1.wav): FAILED ✗
  ├─ File not found in ITTS
  ├─ Log error
  └─ Skip this file
  ↓
File 5 (generated/audio_2.wav): Extracted ✓
  └─ ... Success
  ↓
Mark job: status='partial_failure'
Store error_message: "Failed to extract generated/audio_1.wav: file not in archive"
Update bundle.audio_extraction_status='partial_failure'
  ↓
Playback results:
  ├─ File 1, 2, 3, 5: Available ✓
  └─ File 4: Returns 404 with error details
```

### Recovery Options

**Admin can:**
1. Re-upload the ITTS (retry extraction)
2. Delete the bundle (clean up partial assets)
3. Keep as-is (partial functionality)

---

## Audio Playback Endpoint

### Endpoint Specification

**URL:** `GET /api/bundles/{bundle_id}/audio/{segment_index}`

**Purpose:** Serve pre-extracted WAV file for a specific segment with Range header support.

**Request:**
```http
GET /api/bundles/5/audio/3 HTTP/1.1
Range: bytes=0-1023
```

**Success Response (200 OK):**
```http
HTTP/1.1 200 OK
Content-Type: audio/wav
Content-Length: 245678
Content-Range: bytes 0-1023/245678
Accept-Ranges: bytes

[binary WAV data]
```

**Error Response (404 - Not Extracted):**
```json
{
  "detail": {
    "status": "extraction_in_progress",
    "message": "Audio extraction is currently in progress. Please try again shortly.",
    "bundle_id": 5,
    "segment_index": 3,
    "audio_extraction_status": "extracting",
    "extraction_job_id": 123,
    "job_status": "running",
    "job_progress": 60
  }
}
```

**Error Response (404 - Extraction Failed):**
```json
{
  "detail": {
    "status": "extraction_failed",
    "message": "Audio extraction failed. The bundle cannot be played.",
    "bundle_id": 5,
    "segment_index": 3,
    "audio_extraction_status": "failed",
    "extraction_error_message": "Failed to extract generated/audio_3.wav: corrupted data"
  }
}
```

**Error Response (404 - Audio Not Available):**
```json
{
  "detail": {
    "status": "audio_not_available",
    "message": "Audio file not found. The bundle may have been partially extracted.",
    "bundle_id": 5,
    "segment_index": 3,
    "audio_extraction_status": "partial_failure",
    "extraction_job_id": 123
  }
}
```

### Range Header Support

**Why:** Enables audio seeking/scrubbing in browsers.

**Implementation:**
```python
from fastapi import Request, Response

@router.get("/api/bundles/{bundle_id}/audio/{segment_index}")
async def get_segment_audio(
    bundle_id: int,
    segment_index: int,
    request: Request
):
    # Fetch audio_asset
    # Download from MinIO
    # Handle Range header
    if range_header := request.headers.get("range"):
        start, end = parse_range(range_header)
        return Response(
            content=audio_data[start:end],
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{total}",
                "Accept-Ranges": "bytes"
            }
        )
    else:
        return Response(
            content=audio_data,
            headers={"Accept-Ranges": "bytes"}
        )
```

---

## Cleanup & Deletion Behavior

### When a Bundle is Deleted

```python
async def delete_bundle(bundle_id: int):
    """Delete bundle and cleanup audio assets."""

    # 1. Get all audio_assets linked to this bundle
    audio_assets = await get_bundle_audio_assets(bundle_id)

    # 2. Check reference count for each audio_asset
    for asset in audio_assets:
        ref_count = await count_bundle_references(asset.audio_asset_id)

        # 3. Delete only if this is the only bundle using it
        if ref_count == 1:
            await delete_from_minio(asset.minio_key)
            await delete_audio_asset(asset.id)
        # else: Keep the file (other bundles still need it)

    # 4. bundle_audio_assets records deleted automatically (CASCADE)
    # 5. Bundle record deleted automatically (CASCADE)
    # 6. Original ITTS file kept in MinIO (for backup)
```

### Reference Counting Logic

```python
async def count_bundle_references(audio_asset_id: int) -> int:
    """Count how many bundles reference this audio asset."""
    result = await db.execute(
        select(func.count(BundleAudioAsset.id))
        .where(BundleAudioAsset.audio_asset_id == audio_asset_id)
    )
    return result.scalar() or 0
```

### What Gets Deleted vs Kept

| Item | When Deleted | When Kept |
|------|--------------|-----------|
| Audio asset (MinIO file) | ref_count == 1 | ref_count > 1 (shared) |
| Audio asset record | ref_count == 1 | ref_count > 1 (shared) |
| Bundle record | Always (CASCADE) | N/A |
| bundle_audio_assets records | Always (CASCADE) | N/A |
| Original ITTS file | Never | Always (backup) |

---

## API Changes

### Modified Endpoint: POST /api/bundles

**Current Response:**
```json
{
  "id": 1,
  "title": "My Bundle",
  "filename": "test.itts",
  "s3_key": "bundles/uuid.itts",
  ...
}
```

**New Response:**
```json
{
  "id": 1,
  "title": "My Bundle",
  "filename": "test.itts",
  "s3_key": "bundles/uuid.itts",
  "audio_extraction_status": "extracting",
  "extraction_job_id": 123,
  ...
}
```

### New Endpoint: GET /api/bundles/{id}/audio/{segment_index}

See "Audio Playback Endpoint" section above for full specification.

### Modified Behavior: DELETE /api/bundles/{id}

Now also cleans up audio assets (shared assets preserved via reference counting).

---

## Components & Services

### New Service: ExtractionJobService

```python
class ExtractionJobService:
    def __init__(self, db: AsyncSession, storage: StorageService):
        self.db = db
        self.storage = storage

    async def extract_bundle_audio(self, bundle_id: int, itts_data: bytes):
        """Extract all audio from ITTS bundle."""
        # 1. Download ITTS from MinIO
        # 2. Unpack ZIP
        # 3. Extract each audio file
        # 4. Check SHA-256 for deduplication
        # 5. Upload to MinIO
        # 6. Create audio_assets records
        # 7. Create bundle_audio_assets records
        pass

    async def extract_audio_file(self, bundle_id: int, source_type: str, file_path: str, itts_data: bytes):
        """Extract single audio file with deduplication check."""
        # 1. Extract file from ZIP
        # 2. Calculate SHA-256
        3. Check if audio_asset exists with this SHA256
        # 4. If new: Create record + upload to MinIO
        # 5. If exists: Reuse existing record
        pass

    async def get_audio_asset(self, bundle_id: int, source_type: str, filename: str):
        """Get audio asset for playback."""
        # Query bundle_audio_assets for this bundle
        # Return audio_asset record
        pass
```

### Modified Service: BundleService

```python
async def create_bundle(...):
    # ... existing code ...

    # NEW: Create extraction job
    extraction_job = await job_store.create_job("extraction")

    # Update bundle status
    bundle.audio_extraction_status = "extracting"
    bundle.extraction_job_id = extraction_job

    # Trigger background extraction
    background_tasks.add_task(
        extraction_service.extract_bundle_audio,
        bundle.id,
        itts_data
    )

    await db.commit()
    return bundle_response
```

### New Router: AudioPlayback

```python
@router.get("/api/bundles/{bundle_id}/audio/{segment_index}")
async def get_segment_audio(
    bundle_id: int,
    segment_index: int,
    request: Request
):
    """Serve pre-extracted WAV file with Range header support."""

    # 1. Check bundle.audio_extraction_status
    # 2. If not 'completed': Return helpful 404 with job info
    # 3. Query bundle_audio_assets for segment
    # 4. Download audio from MinIO
    # 5. Handle Range header for seeking
    # 6. Return audio file with proper headers
    pass
```

---

## Data Flow Diagrams

### Upload → Extract → Play Flow

```
┌─────────────┐
│ User Upload│
│ ITTS File   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ POST /api/bundles                   │
│ - SHA-256 check                    │
│ - Create bundle (status=extracting) │
│ - Create extraction job             │
│ - Return bundle_id + job_id         │
└─────────────────────────────────────┘
       │
       ▼ (immediate response)
┌─────────────┐
│ Frontend    │
│ Polls job   │
│ status      │
└─────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Background: ExtractionJobService    │
│ - Download ITTS from MinIO           │
│ - Unpack ZIP                        │
│ - For each audio file:               │
│   ├─ Calculate SHA-256               │
│   ├─ Check audio_assets (dup check)  │
│   ├─ If new: Upload to MinIO         │
│   └─ Link to bundle                 │
│ - Update bundle: status='completed'   │
│ - Mark job: 'completed'               │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ User Plays  │
│ Segment 3   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ GET /api/bundles/5/audio/3          │
│ - Check extraction status             │
│ - Fetch audio_asset from junction     │
│ - Download from MinIO               │
│ - Return audio (200 OK)               │
│ - Supports Range header (seeking)    │
└─────────────────────────────────────┘
       │
       ▼ (instant!)
┌─────────────┐
│ Audio plays  │
│ Immediately  │
└─────────────┘
```

### Duplicate Upload → Asset Reuse Flow

```
┌─────────────┐
│ User Uploads│
│ Same ITTS    │
│ (Again)      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ POST /api/bundles                   │
│ - SHA-256 matches existing bundle     │
│ - Check extraction_job_id           │
│ - If status='completed':            │
│   └─ Reuse existing audio_assets    │
│ - Create new bundle record           │
│ - Link to existing bundle_audio_assets│
│ - Return bundle_id immediately       │
└─────────────────────────────────────┘
       │
       ▼ (fast!)
┌─────────────┐
│ New Bundle  │
│ Created      │
│ Immediately  │
│ Linked to    │
│ Existing     │
│ Assets       │
└─────────────┘
```

---

## Error Handling & Edge Cases

### Edge Case 1: ITTS with Missing Audio Files

**Scenario:** ITTS manifest references `generated/audio_5.wav` but file doesn't exist in ZIP.

**Handling:**
```python
try:
    audio_data = extract_file_from_zip(file_path)
    process_audio(audio_data)
except KeyError:
    logger.warning(f"Audio file not in ITTS: {file_path}")
    mark_extraction_partial_failure(error=f"Missing file: {file_path}")
    continue
```

**Impact:** Other segments still playable, missing segments return 404.

### Edge Case 2: Corrupted Audio File

**Scenario:** File exists but is invalid (not a valid WAV).

**Handling:**
```python
try:
    validate_wav_file(audio_data)
except InvalidWavError:
    logger.error(f"Corrupted audio file: {file_path}")
    mark_extraction_partial_failure(error=f"Invalid WAV: {file_path}")
    continue
```

**Impact:** Other segments still playable.

### Edge Case 3: SHA-256 Collision

**Scenario:** Two different audio files produce same SHA-256 (extremely rare).

**Handling:**
```python
# Before accepting as duplicate
existing_audio = await get_audio_asset_by_sha256(sha256)
if existing_audio:
    # Verify content matches
    if not verify_content_match(new_data, existing_audio.sha256):
        raise CollisionError("SHA-256 collision detected")
```

**Impact:** Prevents serving wrong file.

### Edge Case 4: MinIO Upload Failure

**Scenario:** Extraction succeeds but MinIO upload fails (network, storage full).

**Handling:**
```python
try:
    await storage_service.upload_file(minio_key, audio_data)
except MinIOError as e:
    logger.error(f"Failed to upload audio: {minio_key}")
    mark_extraction_partial_failure(error=f"Upload failed: {e}")
    continue
```

**Impact:** That audio file unavailable, others still work.

### Edge Case 5: Job System Failure

**Scenario:** Job dies before completion (crash, out of memory).

**Handling:**
```python
# Job timeout (5 minutes)
if job.created_at + timedelta(minutes=5) < now():
    if job.status == "extracting":
        await mark_job_failed(job, "Extraction timeout")
        await update_bundle_status(bundle_id, "failed")
```

**Impact:** User sees helpful error, can retry upload.

### Edge Case 6: Concurrent Extraction Jobs

**Scenario:** Two uploads of same ITTS at same time.

**Handling:**
```python
# Second upload checks for existing job
existing_job = await get_job(extraction_job_id)

if existing_job and existing_job.status == "extracting":
    # Queue bundle creation (don't start new job)
    bundle.extraction_job_id = existing_job.id
    # When job completes, this bundle will auto-link
    pass

elif existing_job and existing_job.status == "completed":
    # Just link to existing assets (no extraction)
    pass

else:
    # Create new extraction job
    job = await job_store.create_job("extraction")
    # ... extract ...
```

**Impact:** Efficient - no duplicate extraction work.

---

## Testing Strategy

### Unit Tests

**ExtractionJobService:**
- `test_extract_bundle_audio_success()`
- `test_extract_bundle_audio_partial_failure()`
- `test_extract_audio_file_new_asset()`
- `test_extract_audio_file_duplicate_reuse()`
- `test_sha256_deduplication()`

**BundleService:**
- `test_create_bundle_triggers_extraction()`
- `test_delete_bundle_cleanup_unique_assets()`
- `test_delete_bundle_preserves_shared_assets()`

**AudioAsset CRUD:**
- `test_create_audio_asset()`
- `test_find_asset_by_sha256()`
- `test_count_bundle_references()`

**BundleAudioAsset Junction:**
- `test_link_bundle_to_audio_asset()`
- `test_get_bundle_audio_assets()`
- `test_cascade_delete_bundle()`

### Integration Tests

**Upload → Extract → Play:**
- `test_full_audio_extraction_flow()`
  - Upload ITTS
  - Poll extraction job
  - Verify audio assets created
  - Verify bundle_audio_assets records
  - Play audio via new endpoint
  - Verify Range header support

**Duplicate Upload → Asset Reuse:**
- `test_duplicate_upload_reuses_audio_assets()`
  - Upload ITTS
  - Wait for extraction
  - Upload same ITTS
  - Verify new bundle created
  - Verify audio assets NOT duplicated
  - Verify both bundles can play same audio

**Partial Failure:**
- `test_partial_extraction_playable()`
  - Upload ITTS with one missing file
  - Verify extraction marks as partial_failure
  - Verify available audio still plays
  - Verify missing audio returns helpful 404

**Deletion:**
- `test_delete_bundle_cleanup()`
  - Create bundle with unique audio
  - Delete bundle
  - Verify audio asset deleted from MinIO
  - Verify database records removed

- `test_delete_shared_audio_preserved()`
  - Upload Bundle A (with reference.wav)
  - Upload Bundle B (same reference.wav)
  - Delete Bundle A
  - Verify reference.wav still exists (Bundle B uses it)
  - Delete Bundle B
  - Verify reference.wav deleted (no more references)

**Concurrent Uploads:**
- `test_concurrent_upload_deduplication()`
  - Upload same ITTS twice simultaneously
  - Verify only one extraction job
  - Verify both bundles link to same audio

### Manual Tests

```bash
# 1. Upload ITTS and wait for extraction
curl -X POST http://localhost:8000/api/bundles \
  -F "file=@test.itts"

# 2. Poll extraction status
curl http://localhost:8000/api/jobs/{job_id}

# 3. Play audio directly (instant!)
curl http://localhost:8000/api/bundles/{id}/audio/0 \
  --output segment0.wav

# 4. Test seeking (Range header)
curl -H "Range: bytes=0-1023" \
  http://localhost:8000/api/bundles/{id}/audio/0
```

---

## Implementation Complexity

### Low Complexity
- Database schema (SQLAlchemy models)
- Audio playback endpoint (FastAPI route)
- Job status polling (reuse existing system)
- Response model updates

### Medium Complexity
- ExtractionJobService (unpacking, deduplication logic)
- SHA-256 calculation and validation
- MinIO file management (upload, download, delete)
- Bundle deletion with cascade cleanup

### Key Challenges

1. **Idempotent Extraction**
   - Ensure duplicate SHA-256 checks work correctly
   - Handle race conditions in concurrent uploads

2. **Concurrent Job Management**
   - Queue bundles when extraction in progress
   - Auto-link bundles when extraction completes

3. **Partial Failure Recovery**
   - Keep what works, document what failed
   - Allow retry/re-upload

4. **Cascade Delete with Shared Assets**
   - Reference counting before deletion
   - Preserves shared audio files

5. **Range Header Support**
   - Parse Range header correctly
   - Return 206 Partial Content
   - Handle edge cases (invalid range, out of bounds)

---

## Performance Improvements

### Before Optimization

**Playback Latency:**
- Download ITTS: 2-5 seconds
- Extract ZIP: 1-2 seconds
- Serve audio: 100-200ms
- **Total: 3-7 seconds per playback request**

### After Optimization

**Playback Latency:**
- Serve audio: 100-200ms (direct MinIO GET)
- **Total: 100-200ms per playback request**

**Improvement:** **15-35x faster** for audio playback

### Storage Overhead

- Original ITTS files: Kept (no change)
- Extracted audio files: ~5-10MB per bundle
- Deduplication savings: 20-50% (shared voice audio)

---

## Rollback Plan

If issues arise during implementation:

1. **Disable extraction jobs:** Remove background task trigger
2. **Keep original ITTS files:** Always have the source of truth
3. **Can disable audio endpoint:** Remove route, no impact on existing functionality
4. **Can drop tables:** Clean schema revert if needed
5. **Feature flag:** Add environment variable to enable/disable feature

---

## Future Enhancements

**Not in initial implementation but worth considering:**

1. **Lazy Extraction** (optional)
   - Extract reference/emotion voices immediately
   - Extract generated segments on first playback
   - Trade complexity for storage efficiency

2. **Audio Transcoding** (optional)
   - Store as MP3/Opus to save space
   - Convert on-the-fly for playback
   - Trade CPU for storage

3. **Audio Caching**
   - CDN edge caching for popular audio
   - Cache-Control headers
   - Invalidate on bundle update

4. **Batch Extraction**
   - Extract multiple bundles in one job
   - Useful for bulk operations

5. **Analytics**
   - Track most played audio files
   - Monitor extraction job performance
   - Storage usage statistics

---

## Dependencies

### Existing Dependencies (Already in Use)
- FastAPI - async web framework
- SQLAlchemy - async ORM
- MinIO/python - S3 storage client
- BackgroundTasks - job processing

### New Dependencies
- None! (all functionality uses existing tools)

---

## Timeline Estimate

**Total Implementation Time:** 4-6 hours

- Database schema changes: 1 hour
- ExtractionJobService: 1.5 hours
- Audio playback endpoint: 1 hour
- Bundle service modifications: 30 minutes
- Tests (unit + integration): 1.5 hours
- Documentation updates: 30 minutes

---

## Success Criteria

**Repository is audio-optimized when:**

1. ✅ Audio files extracted after upload (background job)
2. ✅ SHA-256 deduplication for shared audio
3. ✅ Fast playback endpoint (no ZIP extraction)
4. ✅ Range header support (seeking)
5. ✅ Helpful error messages for extraction failures
6. ✅ Shared audio preserved when bundle deleted
7. ✅ All tests passing
8. ✅ Original ITTS files preserved
9. ✅ Frontend can play audio instantly

---

**Status:** ✅ Design Complete

**Next Step:** Create implementation plan using @superpowers:writing-plans skill
