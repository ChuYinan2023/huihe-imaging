from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.imaging_tasks.anonymize_session")
def anonymize_session(self, session_id: int, file_hash: str):
    """Anonymize all DICOM files in an imaging session.

    Idempotent: uses session_id + file_hash as dedup key in Redis.
    """
    import redis
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from pathlib import Path

    from app.core.config import settings
    from app.services.dicom_service import DicomAnonymizer
    from app.models.imaging import (
        ImagingSession,
        ImagingFile,
        ImagingStatus,
        AnonymizationLog,
    )

    # Idempotency check
    r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    idempotency_key = f"anon:{session_id}:{file_hash}"
    if r.get(idempotency_key):
        return {"status": "skipped", "reason": "already processed"}

    # Use sync engine for Celery tasks
    sync_url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)

    with Session(engine) as db:
        session = db.get(ImagingSession, session_id)
        if not session:
            return {"status": "error", "reason": "session not found"}

        if session.status != ImagingStatus.ANONYMIZING:
            return {"status": "skipped", "reason": f"status is {session.status}"}

        anonymizer = DicomAnonymizer()
        files = (
            db.query(ImagingFile)
            .filter(ImagingFile.session_id == session_id)
            .all()
        )

        for file in files:
            if not file.file_path.endswith(".dcm"):
                continue  # Skip non-DICOM files

            input_path = Path(settings.STORAGE_ROOT) / file.file_path
            output_path = (
                Path(settings.STORAGE_ROOT)
                / settings.STORAGE_ANONYMIZED_DIR
                / file.stored_filename
            )

            try:
                result = anonymizer.anonymize(input_path, output_path)
                file.anonymized_path = (
                    f"{settings.STORAGE_ANONYMIZED_DIR}/{file.stored_filename}"
                )

                log = AnonymizationLog(
                    session_id=session_id,
                    file_id=file.id,
                    original_tag_hash=result["original_tag_hash"],
                    strategy_version=result["strategy_version"],
                    private_tags_removed=result["private_tags_removed"],
                    uid_mappings=result["uid_mappings"],
                )
                db.add(log)
            except Exception as exc:
                session.status = ImagingStatus.ANONYMIZE_FAILED
                db.commit()
                raise self.retry(exc=exc)

        session.status = ImagingStatus.COMPLETED
        db.commit()

    # Set idempotency key with TTL
    r.setex(idempotency_key, 3600, "done")
    return {"status": "completed", "session_id": session_id}
