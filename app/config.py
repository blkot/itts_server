from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///data/db/itts.db"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "changeme"
    minio_bucket: str = "itts-bundles"
    minio_secure: bool = False

    # Backup
    backup_schedule: str = "0 2 * * *"
    backup_retention_days: int = 7

    # API
    api_title: str = "ITTS Backend API"
    api_version: str = "0.1.0"


settings = Settings()
