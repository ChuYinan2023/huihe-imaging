from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.ai_tasks.analyze_report")
def analyze_report(self, report_id: int, file_hash: str):
    """Extract text/summary from PDF report using AI.

    Idempotent: uses report_id + file_hash as dedup key.
    Stub implementation - will be connected to actual AI service later.
    """
    import redis
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.models.report import Report

    r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    idempotency_key = f"ai_report:{report_id}:{file_hash}"
    if r.get(idempotency_key):
        return {"status": "skipped", "reason": "already processed"}

    sync_url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)

    with Session(engine) as db:
        report = db.get(Report, report_id)
        if not report:
            return {"status": "error", "reason": "report not found"}

        # Stub: In production, call AI API (Claude Vision, etc.) to analyze PDF
        report.ai_summary = "AI analysis pending - connect to vision model"
        db.commit()

    r.setex(idempotency_key, 3600, "done")
    return {"status": "completed", "report_id": report_id}
