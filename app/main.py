from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
