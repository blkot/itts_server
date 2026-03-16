from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.backup import router as backup_router
from app.api.bundles import router as bundles_router
from app.api.export import router as export_router
from app.api.playlists import router as playlists_router
from app.api.search import router as search_router
from app.config import settings

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bundles_router)
app.include_router(export_router)
app.include_router(playlists_router)
app.include_router(search_router)
app.include_router(backup_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
