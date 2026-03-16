# Frontend Documentation - Purpose & Scope

**IMPORTANT:** These documents are **reference materials** for building a separate frontend application. The ITTS Backend (`itts_server`) is a **pure backend project** and does not include any frontend code.

---

## What This Documentation Is For

These documents provide everything needed to build a frontend application that connects to the ITTS Backend API:

- ✅ Complete API specification (all endpoints, requests, responses)
- ✅ TypeScript type definitions (ready to copy)
- ✅ User workflow descriptions (what users need to do)
- ✅ UI wireframes (visual layout descriptions)
- ✅ Technical requirements (tech stack, dependencies)
- ✅ Feature checklist (development roadmap)

---

## What This Documentation Is NOT

- ❌ Not part of the backend project code
- ❌ Not meant to be hosted with the backend
- ❌ Not required for backend operation
- ❌ Not a frontend application itself

---

## Project Structure

```
itts/                          # Root directory
├── itts_server/               # Backend project (this repo)
│   ├── app/                   # FastAPI application
│   ├── bundle_tools/          # ITTS format utilities
│   ├── tests/                 # Backend tests
│   ├── Dockerfile             # Backend container
│   └── docker-compose.yml     # Services (API + MinIO)
│
└── itts_player/               # Frontend project (separate repo)
    ├── src/                   # Frontend source code
    ├── public/                # Static assets
    └── package.json           # Frontend dependencies
```

---

## How to Use This Documentation

### When Building a Frontend

1. **Create a separate project** for your frontend (React, Vue, etc.)
2. **Copy the TypeScript types** from `typescript-types.md` to your project
3. **Reference the API spec** when making HTTP requests
4. **Follow user workflows** to implement features
5. **Use wireframes** as UI design guidance

### When Working on the Backend

- **Ignore** the `docs/frontend/` folder entirely
- Focus on API endpoints in `app/api/`
- Add tests in `tests/`
- Update `docs/frontend/api-specification.md` if API changes

---

## Communication Protocol

### Backend → Frontend

**Protocol:** HTTP/HTTPS
**Content-Type:** `application/json` (except file uploads)
**Base URL:** `http://localhost:8000` (development)

**Example Request:**
```typescript
// Frontend (separate project)
const response = await fetch('http://localhost:8000/api/bundles');
const bundles = await response.json();
```

**Example Response:**
```json
{
  "items": [...],
  "total": 10,
  "page": 1,
  "page_size": 50
}
```

### CORS Configuration

The backend needs CORS middleware enabled to accept requests from a frontend:

```python
# In itts_server/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## API Documentation

### Interactive API Docs
When the backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Complete API Spec
See [`api-specification.md`](./api-specification.md) for:
- All 18 API endpoints
- Request/response formats
- Error handling
- TypeScript interfaces

---

## Quick Start for Frontend Developers

### 1. Start the Backend

```bash
cd itts_server
docker-compose up -d
curl http://localhost:8000/health
```

### 2. Create Frontend Project

```bash
# Using React + Vite (example)
npm create vite@latest itts_player -- --template react-ts
cd itts_player
npm install
```

### 3. Configure API Connection

```env
# itts_player/.env
VITE_API_URL=http://localhost:8000
```

### 4. Start Building!

Copy types from `typescript-types.md`, reference `user-workflows.md`, and follow `feature-checklist.md`.

---

## Questions?

- **Backend issues:** See [../README.md](../README.md) or [../CLAUDE.md](../CLAUDE.md)
- **API questions:** Check [`api-specification.md`](./api-specification.md) or visit http://localhost:8000/docs
- **Frontend help:** Follow the guides in this folder

---

**Remember:** This documentation is for building a **separate** frontend project. The ITTS Backend is and will remain a **backend-only** service. 🚀
