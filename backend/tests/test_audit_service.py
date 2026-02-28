import pytest
from app.services.audit_service import AuditService, sanitize_value
from app.models.audit import AuditLog
from sqlalchemy import select


def test_sanitize_phone():
    assert sanitize_value("phone", "13812345678") == "138****5678"


def test_sanitize_id_card():
    assert sanitize_value("id_card", "110101199001011234") == "110***********1234"


def test_sanitize_normal_field():
    assert sanitize_value("username", "admin") == "admin"


@pytest.mark.asyncio
async def test_log_action(db_session):
    service = AuditService(db_session)
    await service.log(
        operator_id=1,
        ip="127.0.0.1",
        user_agent="test",
        action="create",
        resource_type="user",
        resource_id="1",
        before_value=None,
        after_value={"username": "admin", "phone": "13812345678"},
    )
    result = await db_session.execute(select(AuditLog))
    log = result.scalar_one()
    assert log.action == "create"
    assert "138****5678" in log.after_value
