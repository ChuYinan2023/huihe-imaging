from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "huihe-imaging"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./huihe.db"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "huihe-imaging"
    JWT_LEEWAY_SECONDS: int = 30
    STORAGE_ROOT: Path = Path("storage")
    STORAGE_TMP_DIR: str = "tmp"
    STORAGE_ORIGINALS_DIR: str = "originals"
    STORAGE_ANONYMIZED_DIR: str = "anonymized"
    STORAGE_REPORTS_DIR: str = "reports"
    STORAGE_SIGNATURES_DIR: str = "signatures"
    MAX_FILE_SIZE_MB: int = 500
    ALLOWED_IMAGE_EXTENSIONS: set = {".dcm", ".jpg", ".jpeg", ".png"}
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    DICOM_UID_PREFIX: str = "2.25."
    DICOM_ANONYMIZATION_SALT: str = "change-me-in-production"
    CSRF_SECRET_KEY: str = "change-me-csrf-secret"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
