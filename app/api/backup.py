from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.backup_service import BackupService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api", tags=["backup"])


@router.post("/backup")
async def create_backup(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Create a manual backup."""
    storage = StorageService()
    service = BackupService(db, storage)
    filename = await service.create_backup()
    created_at = filename.replace("itts-backup-", "").replace(".tar.gz", "")
    return {"filename": filename, "created_at": created_at}


@router.get("/backups")
async def list_backups(db: AsyncSession = Depends(get_db)) -> dict[str, list[str]]:
    """List available backups."""
    storage = StorageService()
    service = BackupService(db, storage)
    backups = await service.list_backups()
    return {"backups": backups}


@router.post("/restore")
async def restore_backup(
    backup: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Restore state from uploaded backup tarball."""
    backup_data = await backup.read()
    if not backup_data:
        raise HTTPException(status_code=422, detail="Backup file is empty")

    storage = StorageService()
    service = BackupService(db, storage)
    return await service.restore_backup(backup_data)
