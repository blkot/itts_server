# ITTS Player - Feature Checklist & Wireframes

This document provides a complete feature checklist and UI wireframe descriptions for the ITTS Player frontend.

---

## Feature Checklist

### Phase 1: Core Features (MVP)

#### Navigation
- [ ] Responsive navigation bar
- [ ] Logo/title
- [ ] Navigation links (Library, Upload, Search, Playlists, Settings)
- [ ] Mobile hamburger menu

#### Library Page
- [ ] Display all bundles in grid/list view
- [ ] Pagination (20-50 items per page)
- [ ] Bundle cards showing:
  - [ ] Title
  - [ ] Filename
  - [ ] Created date
  - [ ] Number of segments
  - [ ] Action buttons (View, Delete)
- [ ] Empty state ("No bundles yet")
- [ ] Loading skeleton

#### Bundle Detail Page
- [ ] Display bundle metadata
- [ ] List all segments with:
  - [ ] Text content
  - [ ] Timing info
  - [ ] Play button for each segment
  - [ ] Multi-select checkboxes
- [ ] Audio player (persistent)
- [ ] Action buttons:
  - [ ] Export selected segments
  - [ ] Delete bundle
  - [ ] Download ITTS file
- [ ] Back to library button

#### Upload Page
- [ ] Drag-and-drop file upload zone
- [ ] File picker button
- [ ] File validation (type, size)
- [ ] Upload progress indicator
- [ ] Duplicate detection handling:
  - [ ] Show existing bundle info
  - [ ] Option to view existing or cancel
- [ ] Success notification
- [ ] Error handling

#### Export Flow
- [ ] Segment selection (multi-select)
- [ ] Export configuration:
  - [ ] Silence between segments (ms input)
  - [ ] Preview selected segments
- [ ] Create export button
- [ ] Job status polling
- [ ] Progress indicator (0-100%)
- [ ] Download button when complete
- [ ] Error handling

#### Search Page
- [ ] Search input (full-text)
- [ ] Filter dropdowns:
  - [ ] Reference voice
  - [ ] Emotion voice
- [ ] Search results display
- [ ] No results message
- [ ] Clear filters button

---

### Phase 2: Advanced Features

#### Pack (Create ITTS from Raw Files)
- [ ] Form with fields:
  - [ ] Title input
  - [ ] Reference voice file upload
  - [ ] Emotion voice file upload
  - [ ] Text lines textarea (one per line)
- [ ] File validation (WAV format)
- [ ] Preview uploaded files
- [ ] Submit button
- [ ] Progress indicator
- [ ] Success/error handling

#### Concatenation
- [ ] Bundle selection interface:
  - [ ] Multi-select from library
  - [ ] Drag-and-drop reordering
  - [ ] Remove from selection
- [ ] Configuration:
  - [ ] Silence between bundles (ms)
- [ ] Preview selected bundles
- [ ] Create concatenation button
- [ ] Job status polling
- [ ] Progress indicator
- [ ] Navigate to new bundle on completion

#### Playlists
- [ ] List all playlists:
  - [ ] Auto-generated (Main, Reference, Emotion, Concats)
  - [ ] User-created
- [ ] Playlist cards:
  - [ ] Name
  - [ ] Description (if manual)
  - [ ] Bundle count
  - [ ] Type indicator (auto/manual)
- [ ] Click to view bundles
- [ ] Create playlist modal:
  - [ ] Name input
  - [ ] Description textarea
  - [ ] Create button
- [ ] Delete playlist (manual only, with confirmation)

---

### Phase 3: Polish & UX

#### Audio Player
- [ ] Persistent audio player (bottom or side)
- [ ] Play/pause control
- [ ] Progress bar with seek
- [ ] Volume control
- [ ] Time display (current / total)
- [ ] Queue support (play multiple segments)
- [ ] Keyboard shortcuts (Space for play/pause)

#### Toast Notifications
- [ ] Success notifications
- [ ] Error notifications
- [ ] Info notifications
- [ ] Auto-dismiss after N seconds
- [ ] Manual dismiss button

#### Loading States
- [ ] Skeleton screens for lists
- [ ] Spinners for single items
- [ ] Progress bars for uploads/exports
- [ ] Optimistic UI updates where appropriate

#### Error States
- [ ] Inline validation errors
- [ ] Error pages (404, 500)
- [ ] Retry buttons
- [ ] Helpful error messages

#### Empty States
- [ ] Illustrations
- [ ] Helpful messages
- [ ] Call-to-action buttons

---

### Phase 4: Settings & Admin

#### Settings Page
- [ ] Application settings
- [ ] Backup management:
  - [ ] Create backup button
  - [ ] List backups
  - [ ] Download backup
  - [ ] Restore backup (upload + confirm)
- [ ] About section

#### User Preferences (Optional)
- [ ] Theme toggle (light/dark)
- [ ] Page size preference
- [ ] Default silence duration
- [ ] Auto-play preference

---

## Wireframe Descriptions

### 1. Layout Shell

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player          [Library] [Upload] [Search]   │
│                      [Playlists] [Settings]          │
├─────────────────────────────────────────────────────┤
│                                                     │
│                                                     │
│                                                     │
│              Main Content Area                      │
│                                                     │
│                                                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### 2. Library Page (Grid View)

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player                    [Search]            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ Bundle  │  │ Bundle  │  │ Bundle  │            │
│  │  Name   │  │  Name   │  │  Name   │            │
│  │         │  │         │  │         │            │
│  │ [View]  │  │ [View]  │  │ [View]  │            │
│  └─────────┘  └─────────┘  └─────────┘            │
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ Bundle  │  │ Bundle  │  │ Bundle  │            │
│  └─────────┘  └─────────┘  └─────────┘            │
│                                                     │
│  [Previous]  Page 1 of 5  [Next]                   │
└─────────────────────────────────────────────────────┘
```

---

### 3. Bundle Detail Page

```
┌─────────────────────────────────────────────────────┐
│  ← Back to Library    Bundle Title                  │
├─────────────────────────────────────────────────────┤
│  Metadata                                          │
│  • Created: March 2, 2026                          │
│  • Segments: 25                                    │
│  • Filename: sample.itts                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Segments                          [Export Selected]│
│                                                     │
│  ☐ [▶] "Hello world"           0:00 - 2:34         │
│  ☐ [▶] "This is a test"        2:34 - 5:12         │
│  ☐ [▶] "Goodbye"               5:12 - 7:45         │
│  ☐ [▶] "See you soon"          7:45 - 10:20        │
│                                                     │
│  [Select All]  [Clear Selection]                   │
└─────────────────────────────────────────────────────┘
```

---

### 4. Upload Page

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player > Upload                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│         ┌─────────────────────────┐                 │
│         │                         │                 │
│         │   Drag & Drop Here      │                 │
│         │   or click to browse    │                 │
│         │                         │                 │
│         └─────────────────────────┘                 │
│                                                     │
│  Supported: .itts files (max 100MB)                │
│                                                     │
│  Uploading: sample.itts  [████████░░] 80%           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### 5. Search Page

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player > Search                               │
├─────────────────────────────────────────────────────┤
│  🔍 [Search keyword...]                             │
│                                                     │
│  Filters:                                           │
│  Reference Voice: [All ▼]  Emotion: [All ▼]       │
│                                                     │
│  Results: 5 bundles found                           │
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ Bundle  │  │ Bundle  │  │ Bundle  │            │
│  └─────────┘  └─────────┘  └─────────┘            │
└─────────────────────────────────────────────────────┘
```

---

### 6. Export Configuration Modal

```
┌─────────────────────────────────────────┐
│  Export Audio                            │
├─────────────────────────────────────────┤
│                                          │
│  Selected Segments: 3                    │
│  • "Hello world"                         │
│  • "This is a test"                      │
│  • "Goodbye"                             │
│                                          │
│  Silence between segments:               │
│  [ 100 ] ms                              │
│                                          │
│  Preview duration: ~15 seconds           │
│                                          │
│  [Cancel]              [Create Export]   │
└─────────────────────────────────────────┘
```

---

### 7. Export Progress

```
┌─────────────────────────────────────────┐
│  Export in Progress                      │
├─────────────────────────────────────────┤
│                                          │
│  Processing segments...                  │
│                                          │
│  ████████████████░░░░░░░░ 60%            │
│                                          │
│  Please wait, this may take a moment...  │
│                                          │
└─────────────────────────────────────────┘
```

---

### 8. Pack (Create ITTS) Page

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player > Create Bundle                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Title: [My Voice Bundle]                           │
│                                                     │
│  Reference Voice:                                   │
│  ┌───────────────────┐  [Choose File]               │
│  │ reference.wav     │                             │
│  └───────────────────┘                             │
│                                                     │
│  Emotion Voice:                                     │
│  ┌───────────────────┐  [Choose File]               │
│  │ emotion.wav       │                             │
│  └───────────────────┘                             │
│                                                     │
│  Text Segments (one per line):                      │
│  ┌────────────────────────────────────────┐         │
│  │ Hello world                            │         │
│  │ This is a test                         │         │
│  │ Goodbye                                │         │
│  └────────────────────────────────────────┘         │
│                                                     │
│  [Cancel]  [Create Bundle]                          │
└─────────────────────────────────────────────────────┘
```

---

### 9. Concatenate Page

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player > Concatenate                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Selected Bundles:                                  │
│                                                     │
│  ┌─────────────────────────────────────────┐       │
│  │ 1. Bundle A                    [Remove] │       │
│  └─────────────────────────────────────────┘       │
│  ┌─────────────────────────────────────────┐       │
│  │ 2. Bundle B                    [Remove] │       │
│  └─────────────────────────────────────────┘       │
│  ┌─────────────────────────────────────────┐       │
│  │ 3. Bundle C                    [Remove] │       │
│  └─────────────────────────────────────────┘       │
│                                                     │
│  [+ Add More Bundles]                               │
│                                                     │
│  Silence between bundles: [ 100 ] ms                │
│                                                     │
│  [Clear All]  [Concatenate]                         │
└─────────────────────────────────────────────────────┘
```

---

### 10. Playlists Page

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player > Playlists                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Auto-Generated                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │ Main (25)      [→] │  │ Reference (10)   [→]│  │
│  └─────────────────────┘  └─────────────────────┘  │
│  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │ Emotion (8)     [→] │  │ Concats (3)      [→]│  │
│  └─────────────────────┘  └─────────────────────┘  │
│                                                     │
│  My Playlists                         [+ New]       │
│  ┌─────────────────────┐                           │
│  │ Favorites (5)   [→] │          [Delete]         │
│  └─────────────────────┘                           │
│  ┌─────────────────────┐                           │
│  │ Work (12)       [→] │          [Delete]         │
│  └─────────────────────┘                           │
└─────────────────────────────────────────────────────┘
```

---

### 11. Settings Page

```
┌─────────────────────────────────────────────────────┐
│  ITTS Player > Settings                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Backup & Restore                                   │
│  ┌─────────────────────────────────────────┐       │
│  │  [Create Backup]                         │       │
│  └─────────────────────────────────────────┘       │
│                                                     │
│  Recent Backups:                                    │
│  • itts-backup-2026-03-02.tar.gz  [Download]       │
│  • itts-backup-2026-03-01.tar.gz  [Download]       │
│                                                     │
│  ┌─────────────────────────────────────────┐       │
│  │  Restore from backup:  [Choose File]    │       │
│  └─────────────────────────────────────────┘       │
│                                                     │
│  About                                              │
│  ITTS Player v1.0.0                                 │
│  © 2026 Your Name                                   │
└─────────────────────────────────────────────────────┘
```

---

### 12. Audio Player (Persistent)

```
┌─────────────────────────────────────────────────────┐
│  ▶   Hello world              ━━━━━●━━━━━  1:23    │
│     2:34                         🔊               │
└─────────────────────────────────────────────────────┘
```

---

## Color Palette Suggestions

### Light Theme
- Primary: `#3B82F6` (Blue 500)
- Secondary: `#8B5CF6` (Violet 500)
- Success: `#10B981` (Emerald 500)
- Error: `#EF4444` (Red 500)
- Background: `#FFFFFF`
- Surface: `#F3F4F6`
- Text: `#1F2937`

### Dark Theme
- Primary: `#60A5FA` (Blue 400)
- Secondary: `#A78BFA` (Violet 400)
- Success: `#34D399` (Emerald 400)
- Error: `#F87171` (Red 400)
- Background: `#111827`
- Surface: `#1F2937`
- Text: `#F9FAFB`

---

## Typography

### Headings
- H1: 2rem (32px), bold
- H2: 1.5rem (24px), semibold
- H3: 1.25rem (20px), semibold

### Body
- Body: 1rem (16px), regular
- Small: 0.875rem (14px), regular
- Caption: 0.75rem (12px), regular

### Font Family
```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

---

## Icon Library Suggestions

- **Lucide React** (Recommended)
  ```bash
  npm install lucide-react
  ```
- **React Icons**
  ```bash
  npm install react-icons
  ```
- **Heroicons** (React)
  ```bash
  npm install @heroicons/react
  ```

---

## Development Priority Order

### Sprint 1: Foundation
1. Layout shell
2. Navigation
3. Library page (view only)
4. Bundle detail page (view only)

### Sprint 2: Core Features
5. Upload functionality
6. Export flow
7. Audio player

### Sprint 3: Advanced
8. Search functionality
9. Pack (create ITTS)
10. Playlists

### Sprint 4: Polish
11. Concatenation
12. Settings/backup
13. Error handling
14. Loading states
15. Responsive design

---

## Accessibility Checklist

- [ ] Keyboard navigation (Tab, Enter, Escape)
- [ ] Focus indicators on all interactive elements
- [ ] ARIA labels for audio controls
- [ ] Alt text for images
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Form error messages in text, not just color
- [ ] Screen reader compatible
- [ ] Keyboard shortcuts documented
