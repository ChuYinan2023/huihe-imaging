import pytest
import pytest_asyncio
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.core.security import hash_password
from datetime import datetime, timezone


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        username="adminaudit",
        email="adminaudit@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin Audit User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcaudit",
        email="crcaudit@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC Audit User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def sample_audit_logs(db_session, admin_user):
    logs = [
        AuditLog(
            operator_id=admin_user.id,
            ip="127.0.0.1",
            user_agent="test-agent",
            action="login",
            resource_type="user",
            resource_id=str(admin_user.id),
        ),
        AuditLog(
            operator_id=admin_user.id,
            ip="127.0.0.1",
            user_agent="test-agent",
            action="create",
            resource_type="project",
            resource_id="1",
        ),
    ]
    for log in logs:
        db_session.add(log)
    await db_session.commit()
    return logs


async def _get_token(client, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_can_list_audit_logs(client, admin_user, sample_audit_logs):
    token = await _get_token(client, "adminaudit", "AdminPass123!")
    response = await client.get(
        "/api/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 2
    # Verify pagination fields
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_non_admin_cannot_list_audit_logs(client, crc_user):
    token = await _get_token(client, "crcaudit", "CrcPass123!")
    response = await client.get(
        "/api/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
