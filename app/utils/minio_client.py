from minio import Minio

from app.config import settings


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


async def ensure_bucket_exists() -> None:
    client = get_minio_client()
    bucket_name = settings.minio_bucket
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
