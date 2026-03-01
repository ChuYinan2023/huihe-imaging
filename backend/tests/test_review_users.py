"""
Review Issue Verification Tests — Users Module

Covers:
  Issue #3:  DEFAULT_PASSWORD hardcoded + reset response missing password info
  Issue #9:  user email update has no uniqueness check
"""

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        username="adminreview",
        email="adminreview@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin Review User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcreview",
        email="crcreview@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC Review User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def second_user(db_session):
    user = User(
        username="secondreview",
        email="secondreview@example.com",
        hashed_password=hash_password("SecondPass123!"),
        full_name="Second Review User",
        role=UserRole.CRC,
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
@pytest.mark.xfail(reason="Review Issue #3: reset response lacks password info for admin")
async def test_issue3_reset_password_response_lacks_password_info(client, db_session, admin_user, crc_user):
    """After password reset, response should include the default/new password value.
    CURRENT: Returns only {"message": "Password reset to default"} — no usable info."""
    token = await _get_token(client, "adminreview", "AdminPass123!")

    response = await client.put(
        f"/api/users/{crc_user.id}/reset-password",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Frontend expects res.data.new_password — should exist
    assert "new_password" in data or "default_password" in data, (
        f"Response should include password info, got keys: {list(data.keys())}"
    )


@pytest.mark.asyncio
async def test_issue3_hardcoded_default_password_works(client, db_session, admin_user, crc_user):
    """Documents that the hardcoded default password 'Huihe@2024' works after reset."""
    admin_token = await _get_token(client, "adminreview", "AdminPass123!")

    # Reset password
    reset_resp = await client.put(
        f"/api/users/{crc_user.id}/reset-password",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reset_resp.status_code == 200

    # Login with the hardcoded default password
    login_resp = await client.post("/api/auth/login", json={
        "username": "crcreview",
        "password": "Huihe@2024",  # hardcoded in users.py:15
    })
    assert login_resp.status_code == 200, "Hardcoded default password should work after reset"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #9: email update has no uniqueness check, returns 500 instead of 409")
async def test_issue9_update_email_to_existing_returns_409(client, db_session, admin_user, crc_user, second_user):
    """Updating user email to one already taken should return 409.
    CURRENT: Returns 500 (DB unique constraint violation) or silently succeeds."""
    token = await _get_token(client, "adminreview", "AdminPass123!")

    response = await client.put(
        f"/api/users/{crc_user.id}",
        json={"email": second_user.email},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should return 409 Conflict with a clear error message
    assert response.status_code == 409, (
        f"Expected 409 for duplicate email, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_issue9_update_email_to_unique_succeeds(client, db_session, admin_user, crc_user):
    """Updating user email to a unique address should succeed."""
    token = await _get_token(client, "adminreview", "AdminPass123!")

    response = await client.put(
        f"/api/users/{crc_user.id}",
        json={"email": "totally-unique-new@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "totally-unique-new@example.com"
