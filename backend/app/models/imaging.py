import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ImagingStatus(str, enum.Enum):
    UPLOADING = "uploading"
    ANONYMIZING = "anonymizing"
    COMPLETED = "completed"
    UPLOAD_FAILED = "upload_failed"
    ANONYMIZE_FAILED = "anonymize_failed"
    REJECTED = "rejected"


class ImagingSession(Base):
    __tablename__ = "imaging_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    center_id: Mapped[int] = mapped_column(Integer, ForeignKey("centers.id"), nullable=False, index=True)
    visit_point: Mapped[str] = mapped_column(String(20), nullable=False)
    imaging_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ImagingStatus] = mapped_column(Enum(ImagingStatus), default=ImagingStatus.UPLOADING)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ImagingFile(Base):
    __tablename__ = "imaging_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_sessions.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    anonymized_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AnonymizationLog(Base):
    __tablename__ = "anonymization_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_sessions.id"), nullable=False, index=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_files.id"), nullable=False)
    original_tag_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    private_tags_removed: Mapped[int] = mapped_column(Integer, default=0)
    uid_mappings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
