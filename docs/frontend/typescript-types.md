# ITTS Player - TypeScript Types & Interfaces

Complete TypeScript type definitions for the ITTS Backend API.

---

## Installation

```bash
# Copy this file to your frontend project
# Path: src/types/api.ts
```

---

## Complete Type Definitions

```typescript
// ========================
// Core Models
// ========================

/**
 * Bundle - ITTS voice bundle
 */
export interface Bundle {
  id: number;
  title: string;
  filename: string;
  s3_key: string;
  manifest_json: string;
  created_at: string;  // ISO 8601 datetime
}

/**
 * Segment - Text segment within a bundle
 */
export interface Segment {
  id: number;
  bundle_id: number;
  text: string;
  reference_index: number;
  emotion_index: number;
  start_time: number;  // milliseconds
  end_time: number;    // milliseconds
}

/**
 * Playlist - Collection of bundles
 */
export interface Playlist {
  id: number;
  name: string;
  description: string | null;
  is_auto_generated: boolean;
  created_at: string;  // ISO 8601 datetime
}

/**
 * Job - Background job status
 */
export interface Job {
  job_id: number;
  status: JobStatus;
  progress: number;  // 0-100
  result_export_id: number | null;
  error_message: string | null;
}

/**
 * JobStatus - Job status enum
 */
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

/**
 * Export - Exported WAV file
 */
export interface Export {
  id: number;
  bundle_id: number;
  segment_indices: number[];
  silence_ms: number;
  s3_key: string;
  created_at: string;  // ISO 8601 datetime
}

/**
 * Backup - Backup file metadata
 */
export interface Backup {
  filename: string;
  created_at: string;  // ISO 8601 datetime
}

// ========================
// Request Types
// ========================

/**
 * CreateExportRequest - Request body for creating export
 */
export interface CreateExportRequest {
  bundle_id: number;
  segment_indices: number[];
  silence_ms: number;
}

/**
 * ConcatBundlesRequest - Request body for concatenating bundles
 */
export interface ConcatBundlesRequest {
  bundle_ids: number[];
  silence_ms: number;
}

/**
 * CreatePlaylistRequest - Request body for creating playlist
 */
export interface CreatePlaylistRequest {
  name: string;
  description?: string;
}

/**
 * PackBundleRequest - Form data for packing bundle
 */
export interface PackBundleRequest {
  title: string;
  reference_voice: File;
  emotion_voice: File;
  text_lines: string;  // Pipe-separated: "Line 1|Line 2|Line 3"
}

// ========================
// Response Types
// ========================

/**
 * PaginatedResponse - Paginated list response
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * BundlesResponse - Response from GET /api/bundles
 */
export type BundlesResponse = PaginatedResponse<Bundle>;

/**
 * CreateJobResponse - Response from POST /api/export or POST /api/concat
 */
export interface CreateJobResponse {
  job_id: number;
}

/**
 * ErrorResponse - API error response
 */
export interface ErrorResponse {
  detail: ErrorDetail;
}

/**
 * ErrorDetail - Error detail object
 */
export interface ErrorDetail {
  status: string;
  message: string;
  existing_bundle?: Bundle;  // For 409 Conflict (duplicate)
}

/**
 * DuplicateUploadError - Specific error for duplicate upload
 */
export interface DuplicateUploadError {
  detail: {
    status: 'duplicate';
    message: string;
    existing_bundle: Bundle;
  };
}

/**
 * CreateBackupResponse - Response from POST /api/backup
 */
export interface CreateBackupResponse {
  filename: string;
  created_at: string;
}

/**
 * BackupsResponse - Response from GET /api/backups
 */
export interface BackupsResponse {
  backups: Backup[];
}

/**
 * RestoreBackupResponse - Response from POST /api/restore
 */
export interface RestoreBackupResponse {
  bundles_restored: number;
  timestamp: string;
}

// ========================
// Search & Filter Types
// ========================

/**
 * SearchParams - Query parameters for search
 */
export interface SearchParams {
  q?: string;      // Full-text search
  ref?: string;    // Filter by reference voice
  emotion?: string; // Filter by emotion voice
}

/**
 * ListBundlesParams - Query parameters for listing bundles
 */
export interface ListBundlesParams {
  page?: number;
  page_size?: number;
}

// ========================
// UI State Types
// ========================

/**
 * AudioPlayerState - Audio player state
 */
export interface AudioPlayerState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isLoading: boolean;
  error: string | null;
}

/**
 * UploadProgress - File upload progress
 */
export interface UploadProgress {
  file: File;
  progress: number;  // 0-100
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
  result?: Bundle;
}

/**
 * SelectionState - Multi-select state for segments
 */
export interface SelectionState {
  selectedIds: Set<number>;
  toggleId: (id: number) => void;
  selectAll: () => void;
  clearSelection: () => void;
  isSelected: (id: number) => boolean;
}

// ========================
// Utility Types
// ========================

/**
 * ApiError - Union type for all possible API errors
 */
export type ApiError =
  | { status: 400; message: string }
  | { status: 404; message: string }
  | { status: 409; message: string; existing_bundle?: Bundle }
  | { status: 500; message: string };

/**
 * BundleWithSegments - Bundle with its segments
 */
export interface BundleWithSegments extends Bundle {
  segments: Segment[];
}

/**
 * PlaylistWithBundles - Playlist with its bundles
 */
export interface PlaylistWithBundles extends Playlist {
  bundles: Bundle[];
}

// ========================
// API Client Types
// ========================

/**
 * ApiClientConfig - Configuration for API client
 */
export interface ApiClientConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
}

/**
 * ApiClient - API client interface
 */
export interface ApiClient {
  // Bundles
  getBundles(params?: ListBundlesParams): Promise<BundlesResponse>;
  getBundle(id: number): Promise<Bundle>;
  deleteBundle(id: number): Promise<void>;
  uploadBundle(file: File): Promise<Bundle>;
  getBundleSegments(id: number): Promise<Segment[]>;

  // Pack
  packBundle(data: PackBundleRequest): Promise<Bundle>;

  // Export
  createExport(request: CreateExportRequest): Promise<CreateJobResponse>;
  getJobStatus(jobId: number): Promise<Job>;
  downloadExport(id: number): Promise<Blob>;

  // Concat
  concatBundles(request: ConcatBundlesRequest): Promise<CreateJobResponse>;

  // Search
  searchBundles(params: SearchParams): Promise<Bundle[]>;

  // Playlists
  getPlaylists(): Promise<Playlist[]>;
  getPlaylistBundles(id: number): Promise<Bundle[]>;
  createPlaylist(request: CreatePlaylistRequest): Promise<Playlist>;
  deletePlaylist(id: number): Promise<void>;

  // Backup
  createBackup(): Promise<CreateBackupResponse>;
  getBackups(): Promise<BackupsResponse>;
  restoreBackup(file: File): Promise<RestoreBackupResponse>;

  // System
  healthCheck(): Promise<{ status: string }>;
}

// ========================
// React Query Types (if using React Query)
// ========================

/**
 * UseBundlesOptions - Options for useBundles hook
 */
export interface UseBundlesOptions {
  page?: number;
  page_size?: number;
  enabled?: boolean;
}

/**
 * UseJobStatusOptions - Options for useJobStatus hook
 */
export interface UseJobStatusOptions {
  refetchInterval?: number | false;
  enabled?: boolean;
}

// ========================
// Component Props Types
// ========================

/**
 * AudioPlayerProps - Audio player component props
 */
export interface AudioPlayerProps {
  src: string;
  autoPlay?: boolean;
  showWaveform?: boolean;
  className?: string;
  onPlay?: () => void;
  onPause?: () => void;
  onEnded?: () => void;
  onError?: (error: Error) => void;
}

/**
 * BundleCardProps - Bundle card component props
 */
export interface BundleCardProps {
  bundle: Bundle;
  onClick?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  showActions?: boolean;
}

/**
 * SegmentListProps - Segment list component props
 */
export interface SegmentListProps {
  segments: Segment[];
  selectedIds?: number[];
  onSelectChange?: (id: number) => void;
  onPlay?: (segment: Segment) => void;
  multiSelect?: boolean;
}

/**
 * FileUploadProps - File upload component props
 */
export interface FileUploadProps {
  accept: string;
  maxSize?: number;  // in bytes
  multiple?: boolean;
  onUpload: (file: File | File[]) => void;
  disabled?: boolean;
}

/**
 * ExportConfigProps - Export configuration component props
 */
export interface ExportConfigProps {
  bundleId: number;
  segments: Segment[];
  onExport: (config: CreateExportRequest) => void;
  loading?: boolean;
}

/**
 * JobStatusProps - Job status component props
 */
export interface JobStatusProps {
  job: Job;
  onComplete?: () => void;
  showProgress?: boolean;
}

// ========================
// Form Types
// ========================

/**
 * PackBundleForm - Pack bundle form state
 */
export interface PackBundleForm {
  title: string;
  reference_voice: File | null;
  emotion_voice: File | null;
  text_lines: string;
}

/**
 * CreatePlaylistForm - Create playlist form state
 */
export interface CreatePlaylistForm {
  name: string;
  description: string;
}

// ========================
// Validation Types
// ========================

/**
 * ValidationError - Form validation error
 */
export interface ValidationError {
  field: string;
  message: string;
}

/**
 * ValidationResult - Form validation result
 */
export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

// ========================
// Pagination Types
// ========================

/**
 * PaginationProps - Pagination component props
 */
export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showFirstLast?: boolean;
  showPrevNext?: boolean;
}

// ========================
// Toast/Notification Types
// ========================

/**
 * ToastProps - Toast notification props
 */
export interface ToastProps {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message?: string;
  duration?: number;
}

// ========================
// Route Types (if using React Router)
// ========================

/**
 * AppRoute - Application route definition
 */
export interface AppRoute {
  path: string;
  element: React.ComponentType;
  protected?: boolean;
}

/**
 * RouteParams - Dynamic route parameters
 */
export interface RouteParams {
  id?: string;
  jobId?: string;
  exportId?: string;
}
```

---

## Usage Examples

### Using with React Query

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import type { Bundle, CreateExportRequest } from '@/types/api';

// Fetch bundles
const { data, isLoading } = useQuery<Bundle[]>({
  queryKey: ['bundles'],
  queryFn: () => fetch('/api/bundles').then(r => r.json()).then(d => d.items)
});

// Create export
const exportMutation = useMutation({
  mutationFn: (data: CreateExportRequest) =>
    fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => r.json())
});
```

### Type-safe API Calls

```typescript
import type { Bundle, Segment } from '@/types/api';

async function getBundleWithSegments(id: number): Promise<Bundle & { segments: Segment[] }> {
  const bundle = await fetch(`/api/bundles/${id}`).then(r => r.json());
  const segments = await fetch(`/api/bundles/${id}/segments`).then(r => r.json());
  return { ...bundle, segments };
}
```

### Form State Management

```typescript
import type { PackBundleForm } from '@/types/api';
import { useState } from 'react';

const [form, setForm] = useState<PackBundleForm>({
  title: '',
  reference_voice: null,
  emotion_voice: null,
  text_lines: ''
});
```

---

## Type Guards

```typescript
/**
 * Check if error is a duplicate upload error
 */
export function isDuplicateError(error: unknown): error is DuplicateUploadError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'detail' in error &&
    typeof error.detail === 'object' &&
    error.detail !== null &&
    'status' in error.detail &&
    error.detail.status === 'duplicate'
  );
}

/**
 * Check if job is complete
 */
export function isJobComplete(status: JobStatus): boolean {
  return status === 'completed' || status === 'failed';
}

/**
 * Check if bundle has segments
 */
export function hasSegments(bundle: Bundle | BundleWithSegments): bundle is BundleWithSegments {
  return 'segments' in bundle && Array.isArray(bundle.segments);
}
```

---

## Export as Module

```typescript
// types/api.ts
export * from './api';
```

```typescript
// Usage in components
import type { Bundle, Segment, CreateExportRequest } from '@/types/api';
```
