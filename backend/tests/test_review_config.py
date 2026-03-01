"""
Review Issue Verification Tests — Config Module

Covers:
  Issue #2: weak default secrets accepted without startup validation in non-DEBUG mode
"""

import pytest


@pytest.mark.xfail(reason="Review Issue #2: no startup validation rejects default secrets in non-DEBUG mode")
def test_issue2_default_secrets_accepted_in_non_debug(monkeypatch):
    """In non-DEBUG mode, Settings should reject default weak secret keys.
    CURRENT: No validation exists — default secrets are silently accepted."""
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

    # Force re-import to pick up new env
    from pydantic_settings import BaseSettings
    from pathlib import Path

    class TestSettings(BaseSettings):
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
        COOKIE_SECURE: bool = False

        model_config = {"env_file": ".env", "extra": "ignore"}

    # This should raise ValueError when DEBUG=False and secrets are defaults
    with pytest.raises(ValueError, match="must be changed"):
        TestSettings()


def test_issue2_document_default_secrets():
    """Document the 3 default weak secret values that should be validated."""
    from app.core.config import Settings

    s = Settings()
    # These are the dangerous defaults — any deployment forgetting .env will use these
    assert s.JWT_SECRET_KEY == "change-me-in-production"
    assert s.DICOM_ANONYMIZATION_SALT == "change-me-in-production"
    assert s.CSRF_SECRET_KEY == "change-me-csrf-secret"
