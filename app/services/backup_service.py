import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import Bundle
from app.services.storage_service import StorageService
from bundle_tools.itts_common import ensure_safe_archive_path


class BackupService:
    def __init__(self, db: AsyncSession, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    async def create_backup(self) -> str:
        """Create full backup tarball with database and metadata, then upload to storage."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        backup_filename = f"itts-backup-{timestamp}.tar.gz"

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            db_path = self._database_path()
            if db_path.is_file():
                tar.add(db_path, arcname="database/itts.db")

            metadata: dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "bundle_count": await self._count_bundles(),
            }
            metadata_bytes = json.dumps(metadata, indent=2).encode("utf-8")
            metadata_file = io.BytesIO(metadata_bytes)
            tarinfo = tarfile.TarInfo("metadata.json")
            tarinfo.size = len(metadata_bytes)
            tar.addfile(tarinfo, metadata_file)

        buffer.seek(0)
        await self.storage.upload_file(backup_filename, buffer.getvalue(), prefix="backups")
        return backup_filename

    async def list_backups(self) -> list[str]:
        """List available backups (placeholder for future object listing support)."""
        return []

    async def restore_backup(self, backup_data: bytes) -> dict[str, Any]:
        """Restore backup database file and return metadata summary."""
        buffer = io.BytesIO(backup_data)
        db_path = self._database_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        metadata: dict[str, Any] = {}
        with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile() or not member.name.startswith("database/"):
                    continue
                relative_name = member.name.replace("database/", "", 1)
                safe_name = ensure_safe_archive_path(relative_name)
                if safe_name != "itts.db":
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                db_path.write_bytes(extracted.read())

            metadata_file = tar.extractfile("metadata.json")
            if metadata_file is not None:
                try:
                    parsed = json.loads(metadata_file.read().decode("utf-8"))
                    if isinstance(parsed, dict):
                        metadata = parsed
                except (UnicodeDecodeError, json.JSONDecodeError):
                    metadata = {}

        return {
            "bundles_restored": int(metadata.get("bundle_count", 0) or 0),
            "timestamp": metadata.get("timestamp"),
        }

    async def _count_bundles(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Bundle))
        return int(result.scalar() or 0)

    @staticmethod
    def _database_path() -> Path:
        raw_url = settings.database_url
        if raw_url.startswith("sqlite:///"):
            db_value = raw_url.replace("sqlite:///", "", 1)
        else:
            db_value = "data/db/itts.db"
        return Path(db_value)
