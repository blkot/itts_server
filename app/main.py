from fastapi import FastAPI

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

app.include_router(bundles_router)
app.include_router(export_router)
app.include_router(playlists_router)
app.include_router(search_router)
app.include_router(backup_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
