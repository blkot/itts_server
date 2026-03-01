from fastapi import FastAPI

from app.api.bundles import router as bundles_router
from app.api.export import router as export_router
from app.config import settings

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

app.include_router(bundles_router)
app.include_router(export_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
