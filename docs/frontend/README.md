# ITTS Player - Frontend Development Guide

Welcome to the ITTS Player frontend documentation. This guide provides everything you need to start building the frontend for the ITTS Backend service.

---

## 📚 Documentation Index

| Document | Description |
|----------|-------------|
| **[API Specification](./api-specification.md)** | Complete API endpoint reference with request/response formats |
| **[User Workflows](./user-workflows.md)** | Detailed user workflows and interaction patterns |
| **[Technical Requirements](./technical-requirements.md)** | Technology stack, dependencies, and implementation guidelines |
| **[TypeScript Types](./typescript-types.md)** | Complete TypeScript type definitions for all API models |
| **[Feature Checklist](./feature-checklist.md)** | Feature list, wireframes, and UI design specifications |

---

## 🚀 Quick Start

### 1. Backend Setup

First, ensure the ITTS Backend is running:

```bash
# Clone the backend repository
cd itts_server

# Start services
docker-compose up -d

# Initialize database
docker-compose exec -T itts-api uv run python -m app.db.init_db

# Verify health
curl http://localhost:8000/health
```

The backend will be available at `http://localhost:8000`

### 2. Frontend Setup

Choose your framework and create a new project:

```bash
# Option 1: React + Vite (Recommended)
npm create vite@latest itts-player -- --template react-ts
cd itts-player
npm install

# Option 2: Vue 3 + Vite
npm create vite@latest itts-player -- --template vue-ts
cd itts-player
npm install

# Option 3: Next.js
npx create-next-app@latest itts-player --typescript
cd itts-player
npm install
```

### 3. Install Dependencies

```bash
# HTTP client
npm install axios

# State management (React)
npm install @tanstack/react-query

# Audio player
npm install howler

# File upload (React)
npm install react-dropzone

# UI components (optional)
npm install lucide-react
npm install clsx tailwind-merge
```

### 4. Configure API Connection

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

### 5. Copy TypeScript Types

Copy the types from `docs/frontend/typescript-types.md` to your project:

```bash
# Create types directory
mkdir src/types

# Copy and save as src/types/api.ts
# (Content from typescript-types.md)
```

---

## 📁 Project Structure

```
itts-player/
├── src/
│   ├── components/          # Reusable components
│   │   ├── AudioPlayer.tsx
│   │   ├── BundleCard.tsx
│   │   ├── SegmentList.tsx
│   │   └── FileUpload.tsx
│   ├── pages/               # Route pages
│   │   ├── Library.tsx
│   │   ├── BundleDetail.tsx
│   │   ├── Upload.tsx
│   │   ├── Search.tsx
│   │   └── Playlists.tsx
│   ├── services/            # API services
│   │   └── api.ts
│   ├── hooks/               # Custom hooks
│   │   ├── useBundles.ts
│   │   ├── useJobStatus.ts
│   │   └── useAudioPlayer.ts
│   ├── types/               # TypeScript types
│   │   └── api.ts
│   ├── utils/               # Utilities
│   │   └── validation.ts
│   ├── App.tsx
│   └── main.tsx
├── public/
│   └── favicon.ico
├── .env
├── package.json
├── tailwind.config.js
└── tsconfig.json
```

---

## 🔧 Configure CORS

Add CORS middleware to the backend (`app/main.py`):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Restart the backend:

```bash
docker-compose restart itts-api
```

---

## 🧪 Test API Connection

Create a test file `src/test-api.ts`:

```typescript
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

async function testConnection() {
  try {
    const response = await axios.get(`${API_URL}/health`);
    console.log('✅ API Connected:', response.data);
  } catch (error) {
    console.error('❌ API Error:', error);
  }
}

testConnection();
```

Run with:

```bash
npm run dev
# Open browser console to see result
```

---

## 📋 Development Checklist

### Phase 1: Foundation
- [ ] Project setup
- [ ] TypeScript configuration
- [ ] API client setup
- [ ] Layout shell (navigation, routing)
- [ ] Environment configuration

### Phase 2: Core Pages
- [ ] Library page (list bundles)
- [ ] Bundle detail page
- [ ] Upload page
- [ ] Search page

### Phase 3: Features
- [ ] Audio player component
- [ ] Export flow (select segments, create job, download)
- [ ] Pack (create ITTS from files)
- [ ] Playlists

### Phase 4: Polish
- [ ] Error handling
- [ ] Loading states
- [ ] Toast notifications
- [ ] Responsive design
- [ ] Accessibility

---

## 🎨 UI Design Resources

### Color Palette
See [Feature Checklist](./feature-checklist.md#color-palette-suggestions) for recommended colors.

### Component Libraries
- **Tailwind CSS** - Utility-first CSS
- **shadcn/ui** - Beautiful accessible components
- **Radix UI** - Unstyled, accessible components

### Icons
- **Lucide React** - Clean & consistent icons
- **Heroicons** - SVG icons by Tailwind Labs

---

## 🔐 Authentication (Future)

Currently, the API has no authentication. For production, consider:

- JWT tokens (store in localStorage or httpOnly cookies)
- OAuth2 (Google, GitHub)
- Session-based auth

Example JWT implementation:

```typescript
// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## 📊 State Management Strategy

### Server State (API Data)
Use **React Query** (@tanstack/react-query) for:
- Automatic caching
- Background refetching
- Optimistic updates
- Deduplication

```typescript
const { data, isLoading } = useQuery({
  queryKey: ['bundles'],
  queryFn: () => fetchBundles()
});
```

### Client State (UI-only)
Use **Zustand** for simple, lightweight state:

```typescript
const useUIStore = create((set) => ({
  selectedSegments: [],
  toggleSegment: (id) => set((state) => ({
    selectedSegments: state.selectedSegments.includes(id)
      ? state.selectedSegments.filter(sid => sid !== id)
      : [...state.selectedSegments, id]
  }))
}));
```

---

## 🧪 Testing

### Unit Tests
```bash
npm install -D vitest @testing-library/react
```

### E2E Tests
```bash
npm install -D playwright
```

---

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

### Deployment Options

1. **Vercel** (Recommended for React/Vite)
   ```bash
   npm install -g vercel
   vercel
   ```

2. **Netlify**
   ```bash
   npm install -g netlify-cli
   netlify deploy --prod
   ```

3. **Static file serving with Nginx**
   ```dockerfile
   FROM nginx:alpine
   COPY dist/ /usr/share/nginx/html/
   ```

---

## 📖 Key Concepts

### How ITTS Files Work

1. **ITTS Format**: ZIP archive containing:
   - `manifest.json` - Metadata
   - `generated/` - Audio files
   - `reference_voice/` - Reference audio
   - `emotion_voice/` - Emotion audio

2. **Upload Flow**:
   - User uploads .itts file
   - Server validates manifest
   - Server calculates SHA-256 (for deduplication)
   - Server stores in MinIO
   - Database record created

3. **Export Flow**:
   - User selects segments
   - Server creates background job
   - Frontend polls job status
   - Server generates WAV file
   - Frontend downloads result

### Key API Concepts

- **Job Polling**: Export and concat operations are async. Poll `/api/jobs/:id` for status.
- **Deduplication**: SHA-256 hash prevents duplicate uploads.
- **Auto-playlists**: Automatically created by voice type (Main, Reference, Emotion, Concats).

---

## 🤝 Contributing

When contributing to the frontend:

1. Follow the existing code style
2. Use TypeScript for type safety
3. Write tests for new features
4. Update documentation
5. Test on multiple browsers

---

## 🐛 Troubleshooting

### CORS Errors
- Ensure CORS middleware is configured in backend
- Check frontend `VITE_API_URL` matches backend URL
- Restart backend after CORS changes

### Audio Not Playing
- Check browser console for errors
- Ensure audio URL is accessible
- Verify Howler.js is initialized correctly
- Check browser autoplay policies

### Upload Fails
- Verify file type (.itts, .wav)
- Check file size limits
- Ensure backend is running
- Check network tab in browser DevTools

---

## 📞 Support

For backend issues, see:
- [Backend README](../../README.md)
- [API Documentation](http://localhost:8000/docs)
- [CLAUDE.md](../../CLAUDE.md) - Backend context

---

## 🎯 Next Steps

1. ✅ Read [API Specification](./api-specification.md)
2. ✅ Read [User Workflows](./user-workflows.md)
3. ✅ Set up frontend project
4. ✅ Configure API connection
5. ✅ Start building!

---

**Happy Coding!** 🚀
