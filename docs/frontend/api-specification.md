# ITTS Backend API Specification

**Version:** 1.0.0
**Base URL:** `http://localhost:8000`
**Content-Type:** `application/json` (unless specified)

---

## Authentication

**Current Status:** No authentication required (all endpoints public)

**Future:** Consider adding JWT/OAuth2 for production

---

## Core Data Models

### Bundle
```typescript
interface Bundle {
  id: number;
  title: string;
  filename: string;
  s3_key: string;
  manifest_json: string;  // JSON string
  created_at: string;     // ISO 8601 datetime
}
```

### Segment
```typescript
interface Segment {
  id: number;
  bundle_id: number;
  text: string;
  reference_index: number;
  emotion_index: number;
  start_time: number;     // milliseconds
  end_time: number;       // milliseconds
}
```

### Playlist
```typescript
interface Playlist {
  id: number;
  name: string;
  description: string | null;
  is_auto_generated: boolean;
  created_at: string;
}
```

### Job
```typescript
interface Job {
  job_id: number;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;        // 0-100
  result_export_id: number | null;
  error_message: string | null;
}
```

### Export
```typescript
interface Export {
  id: number;
  bundle_id: number;
  segment_indices: number[];
  silence_ms: number;
  s3_key: string;
  created_at: string;
}
```

---

## API Endpoints

### 1. System

#### Health Check
```http
GET /health
```

**Response (200):**
```json
{
  "status": "ok"
}
```

---

### 2. Bundles

#### Upload Bundle
```http
POST /api/bundles
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: ITTS file (.itts)

**Success Response (201):**
```json
{
  "id": 1,
  "title": "bundle_name",
  "filename": "file.itts",
  "s3_key": "bundles/uuid.itts",
  "manifest_json": "{...}",
  "created_at": "2026-03-02T10:00:00Z"
}
```

**Duplicate Response (409):**
```json
{
  "detail": {
    "status": "duplicate",
    "message": "This ITTS already exists",
    "existing_bundle": {
      "id": 1,
      ...
    }
  }
}
```

#### List Bundles
```http
GET /api/bundles?page=1&page_size=50
```

**Query Parameters:**
- `page`: number (default: 1)
- `page_size`: number (default: 50)

**Response (200):**
```json
{
  "items": [Bundle],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

#### Get Bundle
```http
GET /api/bundles/:id
```

**Response (200):** `Bundle`

#### Delete Bundle
```http
DELETE /api/bundles/:id
```

**Response (204):** No content

#### Get Bundle Segments
```http
GET /api/bundles/:id/segments
```

**Response (200):** `Segment[]`

---

### 3. Pack (Create ITTS from Raw Files)

#### Pack Files into ITTS
```http
POST /api/bundles/pack
Content-Type: multipart/form-data
```

**Form Data:**
- `title`: string
- `reference_voice`: File (WAV)
- `emotion_voice`: File (WAV)
- `text_lines`: string (pipe-separated: "Line 1|Line 2|Line 3")

**Response (201):** `Bundle`

---

### 4. Export

#### Create Export Job
```http
POST /api/export
Content-Type: application/json
```

**Request Body:**
```json
{
  "bundle_id": 1,
  "segment_indices": [0, 1, 2],
  "silence_ms": 100
}
```

**Response (201):**
```json
{
  "job_id": 123
}
```

#### Get Job Status
```http
GET /api/jobs/:id
```

**Response (200):** `Job`

#### Download Exported WAV
```http
GET /api/export/:id
```

**Response (200):** Binary WAV file (audio/wav)

---

### 5. Concatenation

#### Concatenate Bundles
```http
POST /api/concat
Content-Type: application/json
```

**Request Body:**
```json
{
  "bundle_ids": [1, 2, 3],
  "silence_ms": 100
}
```

**Response (201):**
```json
{
  "job_id": 456
}
```

---

### 6. Search

#### Search Bundles
```http
GET /api/search?q=keyword&ref=voice1&emotion=voice2
```

**Query Parameters:**
- `q`: string (full-text search in title and segment text)
- `ref`: string (filter by reference voice)
- `emotion`: string (filter by emotion voice)

**Response (200):** `Bundle[]`

---

### 7. Playlists

#### List Playlists
```http
GET /api/playlists
```

**Response (200):** `Playlist[]`

#### Get Playlist Bundles
```http
GET /api/playlists/:id/bundles
```

**Response (200):** `Bundle[]`

#### Create Playlist
```http
POST /api/playlists
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "My Playlist",
  "description": "Optional description"
}
```

**Response (201):** `Playlist`

#### Delete Playlist
```http
DELETE /api/playlists/:id
```

**Response (204):** No content

---

### 8. Backup

#### Create Backup
```http
POST /api/backup
```

**Response (200):**
```json
{
  "filename": "itts-backup-2026-03-02.tar.gz",
  "created_at": "2026-03-02T10:00:00Z"
}
```

#### List Backups
```http
GET /api/backups
```

**Response (200):**
```json
{
  "backups": [
    {
      "filename": "itts-backup-2026-03-02.tar.gz",
      "created_at": "2026-03-02T10:00:00Z"
    }
  ]
}
```

#### Restore Backup
```http
POST /api/restore
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: Backup file (.tar.gz)

**Response (200):**
```json
{
  "bundles_restored": 10,
  "timestamp": "2026-03-02T10:00:00Z"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": {
    "status": "error_type",
    "message": "Human readable message"
  }
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `404` - Not Found
- `409` - Conflict (duplicate)
- `500` - Internal Server Error

---

## Rate Limiting

**Current:** No rate limiting

**Future:** Consider implementing rate limiting for production

---

## CORS

**Current:** Not configured (add to FastAPI for frontend)

**Future:** Add CORS middleware for frontend domain
