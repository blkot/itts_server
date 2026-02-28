import io

from fastapi.concurrency import run_in_threadpool
from minio import Minio
from minio.error import S3Error

from app.config import settings
from app.utils.minio_client import get_minio_client
from bundle_tools.itts_common import ensure_safe_archive_path, sha256_bytes


class StorageService:
    def __init__(self, client: Minio | None = None, bucket: str | None = None) -> None:
        self.client = client or get_minio_client()
        self.bucket = bucket or settings.minio_bucket

    async def upload_file(self, filename: str, data: bytes, prefix: str = "") -> str:
        """Upload file bytes to MinIO and return S3 key."""
        s3_key = self._build_s3_key(filename, prefix)
        payload = io.BytesIO(data)
        await run_in_threadpool(
            self.client.put_object,
            self.bucket,
            s3_key,
            payload,
            len(data),
        )
        return s3_key

    async def download_file(self, s3_key: str) -> bytes:
        """Download file bytes from MinIO by key."""
        safe_key = ensure_safe_archive_path(s3_key)
        response = await run_in_threadpool(self.client.get_object, self.bucket, safe_key)
        try:
            data = await run_in_threadpool(response.read)
        finally:
            await run_in_threadpool(response.close)
            await run_in_threadpool(response.release_conn)
        return data

    async def delete_file(self, s3_key: str) -> None:
        """Delete file in MinIO by key."""
        safe_key = ensure_safe_archive_path(s3_key)
        await run_in_threadpool(self.client.remove_object, self.bucket, safe_key)

    async def file_exists(self, s3_key: str) -> bool:
        """Check whether a MinIO object key exists."""
        safe_key = ensure_safe_archive_path(s3_key)
        try:
            await run_in_threadpool(self.client.stat_object, self.bucket, safe_key)
            return True
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return False
            raise

    @staticmethod
    def calculate_data_sha256(data: bytes) -> str:
        """Calculate SHA-256 hash for in-memory bytes."""
        return sha256_bytes(data)

    @staticmethod
    def _build_s3_key(filename: str, prefix: str = "") -> str:
        name = filename.lstrip("/")
        if prefix:
            clean_prefix = prefix.strip("/")
            key = f"{clean_prefix}/{name}"
        else:
            key = name
        return ensure_safe_archive_path(key)
