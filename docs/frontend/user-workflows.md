# ITTS Player - User Workflows

This document describes the key user workflows and interactions for the ITTS Player frontend.

---

## Primary User Personas

### 1. Content Creator
- Uploads raw audio files (reference + emotion voices)
- Creates ITTS bundles with text segments
- Manages library of voice bundles
- Exports custom audio combinations

### 2. Voice Editor
- Searches and filters voice library
- Auditions different voice combinations
- Exports segments for testing
- Organizes voices into playlists

### 3. Consumer
- Browses available voice bundles
- Listens to voice samples
- Downloads exported audio files

---

## Core User Workflows

### Workflow 1: Upload & Create ITTS Bundle

**Goal:** User wants to create a new ITTS bundle from raw audio files.

**Steps:**
1. Navigate to "Upload" or "Create Bundle" page
2. Fill in bundle metadata:
   - Title/name
   - Optional description
3. Upload audio files:
   - Reference voice WAV file
   - Emotion voice WAV file
4. Add text segments (one per line):
   ```
   Hello world
   This is a test
   Goodbye
   ```
5. Click "Create Bundle"
6. System processes files and creates ITTS
7. User sees success message with bundle details
8. Bundle appears in library

**API Calls:**
- `POST /api/bundles/pack`

**Edge Cases:**
- File too large → Show error with size limit
- Invalid WAV format → Validate before upload
- Missing required fields → Show inline validation
- Processing timeout → Show progress indicator

---

### Workflow 2: Upload Existing ITTS File

**Goal:** User has an existing .itts file and wants to add it to the library.

**Steps:**
1. Navigate to "Upload" page
2. Drag & drop or select .itts file
3. System uploads and validates file
4. System calculates SHA-256 (duplicate check)
5. **If duplicate:** Show existing bundle info, ask to confirm
6. **If new:** Add to library, show success
7. Navigate to bundle detail page

**API Calls:**
- `POST /api/bundles`
- `GET /api/bundles/:id`

**Edge Cases:**
- Duplicate detected → Show "Already exists" with link to existing
- Invalid ITTS format → Show specific validation error
- Network timeout → Show retry option

---

### Workflow 3: Browse & Search Library

**Goal:** User wants to find specific voice bundles.

**Steps:**
1. Navigate to "Library" page
2. View paginated list of bundles
3. **Search by keyword:**
   - Type in search box
   - Results filter in real-time
   - Search matches title and segment text
4. **Filter by voice type:**
   - Select reference voice from dropdown
   - Select emotion voice from dropdown
   - Can combine filters
5. Click on bundle to view details

**API Calls:**
- `GET /api/bundles?page=1&page_size=20`
- `GET /api/search?q=keyword&ref=voice&emotion=mood`

**UI States:**
- Loading state (skeleton)
- Empty state (no results)
- Error state (retry button)
- Results grid/list view

---

### Workflow 4: View Bundle Details

**Goal:** User wants to see detailed information about a bundle.

**Steps:**
1. Click on bundle from library/search
2. Navigate to bundle detail page
3. See:
   - Bundle title, filename, created date
   - Text segments list with timing
   - Audio player for each segment
   - Action buttons (export, delete, download)
4. Play individual segments
5. Select multiple segments for export

**API Calls:**
- `GET /api/bundles/:id`
- `GET /api/bundles/:id/segments`

**UI Components:**
- Bundle metadata card
- Segments list with play buttons
- Multi-select checkboxes
- Bulk action toolbar

---

### Workflow 5: Export Custom Audio

**Goal:** User wants to create a custom WAV file from selected segments.

**Steps:**
1. From bundle detail page, select segments:
   - Checkbox for each segment
   - "Select All" option
2. Configure export settings:
   - Silence between segments (ms)
   - Default: 100ms
3. Click "Export" button
4. System creates export job
5. Show progress indicator:
   - Job status (pending → running → completed)
   - Progress bar (0-100%)
6. When complete:
   - Show download button
   - Auto-download option

**API Calls:**
- `POST /api/export` → creates job
- Poll `GET /api/jobs/:id` → check status
- `GET /api/export/:id` → download WAV

**UI States:**
- Configuring export
- Exporting (progress bar)
- Ready to download
- Downloaded

**Polling Strategy:**
- Poll every 1 second
- Stop after 30 seconds (show error)
- Use WebSocket if available (future)

---

### Workflow 6: Concatenate Bundles

**Goal:** User wants to merge multiple bundles into one.

**Steps:**
1. Navigate to "Concatenate" page
2. Select multiple bundles from library:
   - Multi-select interface
   - Drag to reorder
3. Configure settings:
   - Silence between bundles (ms)
4. Click "Concatenate"
5. System processes (may take time)
6. Show progress
7. When complete:
   - Show new bundle details
   - Navigate to new bundle

**API Calls:**
- `POST /api/concat` → creates job
- Poll `GET /api/jobs/:id` → check status

**UI Considerations:**
- Drag-and-drop reordering
- Visual preview of selected bundles
- Progress indicator for long operation

---

### Workflow 7: Manage Playlists

**Goal:** User wants to organize bundles into playlists.

**Steps:**
1. Navigate to "Playlists" page
2. View auto-generated playlists:
   - Main
   - Reference voices (grouped by name)
   - Emotion voices (grouped by name)
   - Concats
3. View manual playlists:
   - User-created collections
4. Click playlist to view bundles
5. Create new playlist:
   - Click "Create Playlist"
   - Enter name and description
   - Add bundles (drag or select)
6. Delete playlist (manual only)

**API Calls:**
- `GET /api/playlists`
- `GET /api/playlists/:id/bundles`
- `POST /api/playlists`
- `DELETE /api/playlists/:id`

**UI Components:**
- Playlist cards
- Bundle grid within playlist
- Create playlist modal
- Delete confirmation

---

### Workflow 8: Delete Bundle

**Goal:** User wants to remove a bundle from the library.

**Steps:**
1. From bundle detail page, click "Delete"
2. Show confirmation dialog:
   - "Are you sure?"
   - "This cannot be undone"
3. User confirms
4. System deletes bundle from database and storage
5. Show success message
6. Navigate back to library

**API Calls:**
- `DELETE /api/bundles/:id`

**UI Considerations:**
- Destructive action warning
- Confirmation dialog
- Toast notification
- Optimistic UI update (remove from list)

---

## Secondary Workflows

### Workflow 9: Download Bundle File

**Goal:** User wants to download the original .itts file.

**Steps:**
1. From bundle detail page, click "Download ITTS"
2. Browser downloads file
3. Show success notification

**API Calls:**
- `GET /api/bundles/:id/download` (if implemented)
- Or download from storage directly

---

### Workflow 10: Backup & Restore

**Goal:** Admin user wants to backup or restore the library.

**Steps:**
1. Navigate to "Settings" or "Admin" page
2. Click "Create Backup"
3. System creates backup tarball
4. Show backup filename and date
5. Download backup file
6. **Restore:**
   - Upload backup file
   - System validates and restores
   - Show summary (bundles restored)

**API Calls:**
- `POST /api/backup`
- `GET /api/backups`
- `POST /api/restore`

---

## User Flow Diagrams

### Main Navigation Flow
```
┌─────────────┐
│   Landing   │
│   Page      │
└──────┬──────┘
       │
       ├─→ Library (Browse All)
       ├─→ Upload (Create Bundle)
       ├─→ Search (Find Voices)
       ├─→ Playlists (Organized)
       └─→ Settings (Backup/Restore)
```

### Export Flow
```
Bundle Detail
     ↓
Select Segments
     ↓
Configure Export
     ↓
Create Job (POST /api/export)
     ↓
Poll Status (GET /api/jobs/:id)
     ↓
  ┌───┴───┐
  ↓       ↓
Completed  Failed
  ↓         ↓
Download  Show Error
```

---

## UI States & Feedback

### Loading States
- Skeleton screens for lists
- Spinner for single item loads
- Progress bar for long operations

### Error States
- Inline validation errors
- Toast notifications for actions
- Error pages for 404, 500
- Retry buttons where applicable

### Success Feedback
- Toast notifications
- Success messages
- Auto-navigation after success

### Empty States
- "No bundles found" illustration
- "Upload your first bundle" CTA
- Helpful hints for getting started

---

## Responsive Design

### Desktop (> 1024px)
- Multi-column layout
- Sidebar navigation
- Large audio players
- Bulk action toolbar

### Tablet (768px - 1024px)
- Two-column layout
- Collapsible sidebar
- Medium audio players

### Mobile (< 768px)
- Single column layout
- Bottom navigation or hamburger menu
- Compact audio players
- Full-screen modals for forms

---

## Accessibility

- Keyboard navigation support
- Screen reader compatibility
- Focus indicators
- ARIA labels for audio players
- Error messages in text (not color alone)
- Sufficient color contrast
