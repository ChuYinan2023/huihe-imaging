import hashlib
import uuid
from pathlib import Path

from app.core.config import settings


ALLOWED_MIMES = {
    "application/dicom", "application/octet-stream",  # DICOM
    "image/jpeg", "image/png",
}
ALLOWED_EXTENSIONS = settings.ALLOWED_IMAGE_EXTENSIONS


def validate_file(filename: str, content_type: str | None) -> bool:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    if content_type and content_type not in ALLOWED_MIMES:
        # Allow octet-stream for DICOM files
        if ext == ".dcm" and content_type == "application/octet-stream":
            return True
        if content_type not in ALLOWED_MIMES:
            return False
    return True


def compute_file_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_stored_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"
