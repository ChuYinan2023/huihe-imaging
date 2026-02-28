import pytest
from app.models.audit import AuditLog
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_audit_log(db_session):
    log = AuditLog(
        operator_id=1,
        ip="192.168.1.1",
        user_agent="Mozilla/5.0",
        action="create_user",
        resource_type="user",
        resource_id="1",
        before_value=None,
        after_value='{"username":"admin"}',
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(select(AuditLog))
    saved = result.scalar_one()
    assert saved.action == "create_user"
    assert saved.ip == "192.168.1.1"
