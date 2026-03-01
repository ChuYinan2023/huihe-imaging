"""
Review Issue Verification Tests — Audit Module

Covers:
  Issue #7:  audit log date filter uses string comparison vs DateTime
  Issue #8:  audit log response field name mismatch (timestamp vs created_at)
  Issue #14: X-Forwarded-For unconditionally trusted (IP spoofing)
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        username="adminauditrev",
        email="adminauditrev@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin Audit Review",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _get_token(client, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #7: date filter uses string comparison vs DateTime — returns 0 results")
async def test_issue7_date_filter_with_string(client, db_session, admin_user):
    """Test that date_from/date_to string parameters filter audit logs correctly.
    CURRENT: String-vs-DateTime comparison returns 0 results in SQLite."""
    now = datetime.now(timezone.utc)

    # Create logs at known times
    for i, delta_days in enumerate([-3, -1, 0]):
        log = AuditLog(
            operator_id=admin_user.id,
            ip="127.0.0.1",
            action=f"test_action_{i}",
            resource_type="test",
            resource_id=str(i),
            timestamp=now + timedelta(days=delta_days),
        )
        db_session.add(log)
    await db_session.commit()

    token = await _get_token(client, "adminauditrev", "AdminPass123!")

    # Filter for today only
    today_str = now.strftime("%Y-%m-%d")
    response = await client.get(
        f"/api/audit?date_from={today_str}&date_to={today_str}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Should return at least the log from today + login audit log
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_issue7_date_filter_with_iso_format(client, db_session, admin_user):
    """Test ISO datetime format in date filters."""
    token = await _get_token(client, "adminauditrev", "AdminPass123!")

    now = datetime.now(timezone.utc)
    iso_str = now.strftime("%Y-%m-%dT%H:%M:%S")

    response = await client.get(
        f"/api/audit?date_from={iso_str}",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should not crash — may or may not filter correctly depending on DB behavior
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_issue8_audit_response_field_names(client, db_session, admin_user):
    """Documents the actual field names in audit log responses.
    Backend uses 'timestamp', frontend expects 'created_at' — mismatch."""
    # Login creates an audit log entry
    token = await _get_token(client, "adminauditrev", "AdminPass123!")

    response = await client.get(
        "/api/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

    item = data["items"][0]
    expected_fields = {"id", "operator_id", "ip", "user_agent", "timestamp", "action",
                       "resource_type", "resource_id", "before_value", "after_value"}

    actual_fields = set(item.keys())
    assert expected_fields == actual_fields, (
        f"Expected fields {expected_fields}, got {actual_fields}"
    )

    # Document: backend returns "timestamp", NOT "created_at"
    assert "timestamp" in item, "Backend returns 'timestamp' field"
    assert "created_at" not in item, "Backend does NOT return 'created_at' (frontend expects it)"

    # Document: backend does NOT return "operator_name"
    assert "operator_name" not in item, "Backend does NOT return 'operator_name' (frontend expects it)"


@pytest.mark.asyncio
async def test_issue14_xff_spoofing_recorded_in_audit(client, db_session, admin_user):
    """Documents that X-Forwarded-For values are blindly recorded in audit logs."""
    spoofed_ip = "1.2.3.4"

    # Login with spoofed X-Forwarded-For
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "adminauditrev", "password": "AdminPass123!"},
        headers={"X-Forwarded-For": f"{spoofed_ip}, 10.0.0.1"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Check audit log
    response = await client.get(
        "/api/audit?action=login",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

    # The first IP from X-Forwarded-For should be recorded
    login_log = data["items"][0]
    assert login_log["ip"] == spoofed_ip, (
        f"Expected spoofed IP '{spoofed_ip}', got '{login_log['ip']}'"
    )


@pytest.mark.asyncio
async def test_issue14_arbitrary_xff_value_accepted(client, db_session, admin_user):
    """Documents that arbitrary (non-IP) values in X-Forwarded-For are accepted."""
    arbitrary_value = "evil-spoofed-not-an-ip"

    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "adminauditrev", "password": "AdminPass123!"},
        headers={"X-Forwarded-For": arbitrary_value},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/audit?action=login",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Find the login log with the arbitrary IP
    found = any(item["ip"] == arbitrary_value for item in data["items"])
    assert found, f"Arbitrary X-Forwarded-For value '{arbitrary_value}' was recorded without validation"
