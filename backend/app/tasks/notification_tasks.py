from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.notification_tasks.send_sms")
def send_sms(self, phone: str, message: str, idempotency_key: str):
    """Send SMS notification. Stub for external SMS provider.

    Idempotent via idempotency_key.
    """
    import redis
    from app.core.config import settings

    r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    if r.get(f"sms:{idempotency_key}"):
        return {"status": "skipped", "reason": "already sent"}

    # Stub: In production, call SMS provider API (Aliyun SMS, etc.)
    # sms_client.send(phone=phone, message=message)

    r.setex(f"sms:{idempotency_key}", 3600, "sent")
    return {"status": "sent", "phone": phone}
