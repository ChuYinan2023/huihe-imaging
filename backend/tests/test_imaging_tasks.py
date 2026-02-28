import pytest
from app.tasks.celery_app import celery_app


def test_celery_app_config():
    assert celery_app.main == "huihe-imaging"
    assert "app.tasks.imaging_tasks.*" in celery_app.conf.task_routes


def test_task_routing():
    routes = celery_app.conf.task_routes
    assert routes["app.tasks.imaging_tasks.*"]["queue"] == "imaging"
    assert routes["app.tasks.ai_tasks.*"]["queue"] == "ai"
    assert routes["app.tasks.notification_tasks.*"]["queue"] == "notification"
