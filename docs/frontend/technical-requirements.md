# ITTS Player - Technical Requirements

This document outlines technical considerations and requirements for the ITTS Player frontend.

---

## Technology Stack Recommendations

### Frontend Framework Options

#### Option 1: React + TypeScript (Recommended)
- **Pros:** Large ecosystem, TypeScript support, great audio libraries
- **Libraries:** React Router, Axios, React Query, Howler.js
- **UI:** Material-UI, Tailwind CSS, or Chakra UI

#### Option 2: Vue 3 + TypeScript
- **Pros:** Simpler learning curve, excellent TypeScript support
- **Libraries:** Vue Router, Pinia, Howler.js
- **UI:** Vuetify, Element Plus, or PrimeVue

#### Option 3: Svelte + TypeScript
- **Pros:** Lightweight, compiled, great performance
- **Libraries:** SvelteKit, Howler.js
- **UI:** Skeleton UI, Tailwind CSS

#### Option 4: Next.js (React-based)
- **Pros:** SSR, API routes, great SEO, file-based routing
- **Libraries:** Built-in React, Next.js Audio
- **UI:** Tailwind CSS, shadcn/ui

---

## Required Dependencies

### Core
- **Routing:** React Router / Vue Router / etc.
- **HTTP Client:** Axios or fetch API
- **State Management:** React Query / SWR / Pinia / Zustand
- **TypeScript:** For type safety

### Audio Handling
- **Howler.js:** Audio playback with fallbacks
  ```bash
  npm install howler
  # or
  yarn add howler
  ```
- **Alternative:** HTML5 Audio API (native)

### File Upload
- **Dropzone.js:** Drag-and-drop file uploads
  ```bash
  npm install react-dropzone  # for React
  ```
- **Alternative:** Native HTML5 file input

### UI Components
- **Date/Time:** date-fns or dayjs
- **Forms:** React Hook Form / VeeValidate
- **Notifications:** react-toastify / vue-toastification
- **Modals:** React Modal / Vue Modal
- **Pagination:** React Paginate / Vue Paginate

### Development Tools
- **ESLint:** Code linting
- **Prettier:** Code formatting
- **Vite:** Fast dev server and build tool

---

## State Management Strategy

### Server State (API Data)
Use a server state library instead of manual useState:
- **React Query / SWR:** Caching, refetching, optimistic updates
- **Benefits:** Automatic caching, background refetch, deduplication

### Client State (UI-only)
Use lightweight state management:
- **Zustand / Jotai:** Simple, minimal
- **Context API:** Built-in React
- **Pinia:** Vue 3

### Example State Structure
```typescript
// Server state (React Query)
const { data: bundles, isLoading } = useQuery({
  queryKey: ['bundles', page],
  queryFn: () => fetchBundles(page)
});

// Client state (Zustand)
const useUIStore = create((set) => ({
  selectedSegments: [],
  setSelectedSegments: (segments) => set({ selectedSegments: segments })
}));
```

---

## Audio Player Requirements

### Features Needed
1. **Play/Pause** control
2. **Seek** bar (progress)
3. **Volume** control
4. **Loading** state
5. **Error** handling
6. **Time display** (current / total)
7. **Waveform visualization** (optional)

### Implementation Options

#### Option 1: Howler.js (Recommended)
```typescript
import { Howl } from 'howler';

const sound = new Howl({
  src: ['http://localhost:8000/api/export/123'],
  html5: true,  // Force HTML5 Audio
  format: ['wav']
});

sound.play();
sound.pause();
sound.seek(30);  // Seek to 30 seconds
```

#### Option 2: HTML5 Audio API
```typescript
const audio = new Audio('http://localhost:8000/api/export/123');
audio.play();
audio.pause();
audio.currentTime = 30;
```

### Audio Player Component Props
```typescript
interface AudioPlayerProps {
  src: string;           // Audio URL
  autoPlay?: boolean;    // Auto-play on mount
  showWaveform?: boolean; // Show waveform visualization
  onPlay?: () => void;   // Callback when playing
  onPause?: () => void;  // Callback when paused
  onEnded?: () => void;  // Callback when finished
  onError?: (error) => void; // Error handler
}
```

---

## File Upload Requirements

### Upload Scenarios
1. **Upload ITTS file** (.itts)
2. **Upload WAV files** (for pack operation)
3. **Upload backup file** (.tar.gz)

### File Validation
```typescript
// Validate file type
const validateFileType = (file: File, allowedTypes: string[]) => {
  return allowedTypes.includes(file.type);
};

// Validate file size (e.g., max 100MB)
const validateFileSize = (file: File, maxSizeMB: number) => {
  return file.size <= maxSizeMB * 1024 * 1024;
};

// Example usage
validateFileType(file, ['application/octet-stream', 'audio/wav']);
validateFileSize(file, 100);  // 100MB max
```

### Upload Progress
```typescript
// Axios upload with progress
const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post('/api/bundles', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const progress = Math.round(
        (progressEvent.loaded * 100) / (progressEvent.total || 1)
      );
      // Update progress UI
    }
  });

  return response.data;
};
```

---

## Polling & Real-time Updates

### Job Status Polling
```typescript
// Poll job status until complete
const pollJobStatus = async (
  jobId: number,
  onUpdate: (status: Job) => void,
  intervalMs = 1000
) => {
  const poll = async () => {
    const response = await axios.get(`/api/jobs/${jobId}`);
    const job = response.data;

    onUpdate(job);

    if (job.status === 'completed' || job.status === 'failed') {
      return job;  // Done
    }

    // Continue polling
    await new Promise(resolve => setTimeout(resolve, intervalMs));
    return poll();
  };

  return poll();
};

// Usage
pollJobStatus(123, (job) => {
  console.log('Job progress:', job.progress);
});
```

### Polling with React Query
```typescript
const useJobStatus = (jobId: number) => {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => axios.get(`/api/jobs/${jobId}`).then(r => r.data),
    refetchInterval: (data) => {
      // Poll every second until complete
      return data?.status === 'completed' || data?.status === 'failed'
        ? false  // Stop polling
        : 1000;  // Continue polling
    }
  });
};
```

---

## Error Handling

### Global Error Handler
```typescript
// Axios interceptor
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 409 Conflict (duplicate)
    if (error.response?.status === 409) {
      const existingBundle = error.response.data.detail.existing_bundle;
      toast.error('Bundle already exists', {
        description: `Bundle ID: ${existingBundle.id}`
      });
      return Promise.reject(error);
    }

    // Handle 404 Not Found
    if (error.response?.status === 404) {
      toast.error('Resource not found');
      return Promise.reject(error);
    }

    // Handle 500 Server Error
    if (error.response?.status === 500) {
      toast.error('Server error, please try again');
      return Promise.reject(error);
    }

    // Network error
    if (!error.response) {
      toast.error('Network error, check your connection');
      return Promise.reject(error);
    }

    return Promise.reject(error);
  }
);
```

---

## CORS Configuration

### Backend Setup (FastAPI)
Add CORS middleware to `app/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Frontend Configuration
```typescript
// Axios base URL
const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: false,  // Set to true if using cookies
});
```

---

## Performance Considerations

### Pagination
- Use pagination for large lists (default: 20-50 items)
- Infinite scroll vs. pagination controls
- Prefetch next page

### Image/Asset Optimization
- Lazy load images
- Use WebP format when possible
- Serve thumbnails for audio waveforms

### Bundle Size
- Code splitting by route
- Lazy load audio player component
- Tree shake unused dependencies

### Caching Strategy
- Use React Query's built-in caching
- Cache API responses (5-15 minutes)
- Revalidate on focus/window focus

---

## Security Considerations

### File Upload Validation
- Validate file type on client
- Validate file size before upload
- Never trust client-side validation only

### XSS Prevention
- Sanitize user input (bundle titles, descriptions)
- Use React/Vue's built-in XSS protection
- Avoid `dangerouslySetInnerHTML`

### CSRF Protection
- If adding authentication, implement CSRF tokens
- Use SameSite cookie attribute

---

## Environment Configuration

### Development
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=ITTS Player
```

### Production
```env
VITE_API_URL=https://api.itts.example.com
VITE_APP_NAME=ITTS Player
```

### Usage
```typescript
const API_URL = import.meta.env.VITE_API_URL;
```

---

## Build & Deployment

### Build Commands
```bash
# Development
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

### Deployment Options
1. **Static Hosting:** Vercel, Netlify, GitHub Pages
2. **Docker Container:** Nginx serving static files
3. **Same Server:** Serve from FastAPI static files

---

## Browser Compatibility

### Target Browsers
- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile Safari: iOS 14+
- Chrome Mobile: Android 10+

### Polyfills Needed
- `fetch` API (use Axios instead)
- `URL` API (widely supported)
- Audio API (widely supported)

---

## Testing Strategy

### Unit Tests
- Test components in isolation
- Mock API calls
- Use Vitest or Jest

### Integration Tests
- Test user flows
- Test API integration
- Use Playwright or Cypress

### Test Coverage Goals
- Components: 80%+
- Critical paths: 100%
- Error handling: 100%

---

## Monitoring & Analytics

### Recommended Tools
- **Error Tracking:** Sentry
- **Analytics:** Plausible (privacy-friendly) or Google Analytics
- **Performance:** Web Vitals

### Events to Track
- Page views
- Bundle uploads
- Export creations
- Downloads
- Errors

---

## Accessibility (WCAG 2.1 AA)

### Requirements
- Keyboard navigation
- Screen reader compatibility
- Focus indicators
- Color contrast (4.5:1 for text)
- ARIA labels for audio players
- Error messages in text
