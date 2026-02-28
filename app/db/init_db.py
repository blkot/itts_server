from app.db.session import Base, async_engine
from app.models import database  # noqa: F401


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
