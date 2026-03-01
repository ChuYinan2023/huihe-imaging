"""
Review Issue Verification Tests — Auth Module

Covers:
  Issue #1:  logout does not revoke server-side refresh token
  Issue #15: expired refresh tokens are never cleaned up
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, func

from app.core.security import hash_password, hash_token
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        username="authreview",
        email="authreview@example.com",
        hashed_password=hash_password("AuthPass123!"),
        full_name="Auth Review User",
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
@pytest.mark.xfail(reason="Review Issue #1: logout does not invalidate refresh token in DB")
async def test_issue1_logout_should_invalidate_refresh_token_in_db(client, db_session, test_user):
    """After logout, all refresh tokens for the user/family should be marked used=True."""
    # Login
    login_resp = await client.post("/api/auth/login", json={
        "username": "authreview",
        "password": "AuthPass123!",
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Verify refresh token exists and is unused
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == test_user.id, RefreshToken.used == False)  # noqa: E712
    )
    unused_before = result.scalars().all()
    assert len(unused_before) >= 1, "Should have at least one unused refresh token after login"

    # Logout
    logout_resp = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200

    # Check DB: all tokens should now be used
    await db_session.expire_all()
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == test_user.id, RefreshToken.used == False)  # noqa: E712
    )
    unused_after = result.scalars().all()
    assert len(unused_after) == 0, "All refresh tokens should be marked used after logout"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #1: refresh token usable after logout")
async def test_issue1_refresh_after_logout_should_fail(client, db_session, test_user):
    """After logout, using the old refresh token cookie to refresh should return 401."""
    # Login
    login_resp = await client.post("/api/auth/login", json={
        "username": "authreview",
        "password": "AuthPass123!",
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Extract the refresh_token cookie value from response
    refresh_cookie = login_resp.cookies.get("refresh_token")
    # If cookies not directly accessible via httpx, check headers
    if not refresh_cookie:
        for header_name, header_val in login_resp.headers.multi_items():
            if header_name.lower() == "set-cookie" and "refresh_token=" in header_val:
                refresh_cookie = header_val.split("refresh_token=")[1].split(";")[0]
                break

    assert refresh_cookie, "Login should set a refresh_token cookie"

    # Logout
    await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try refresh with the old cookie — should fail
    refresh_resp = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": refresh_cookie},
    )
    assert refresh_resp.status_code == 401, "Refresh after logout should be rejected"


@pytest.mark.asyncio
async def test_issue15_expired_tokens_accumulate(client, db_session, test_user):
    """Documents that expired RefreshToken rows are never cleaned up."""
    # Insert expired tokens directly into DB
    past = datetime.now(timezone.utc) - timedelta(days=30)
    for i in range(5):
        rt = RefreshToken(
            user_id=test_user.id,
            token_hash=hash_token(f"expired-token-{i}"),
            jti=f"expired-jti-{i}",
            family_id=f"expired-family-{i}",
            used=True,
            expires_at=past,
        )
        db_session.add(rt)
    await db_session.commit()

    # Login to create a new token
    await client.post("/api/auth/login", json={
        "username": "authreview",
        "password": "AuthPass123!",
    })

    # Count all tokens — expired ones should still be there
    result = await db_session.execute(
        select(func.count(RefreshToken.id)).where(RefreshToken.user_id == test_user.id)
    )
    total = result.scalar()
    # 5 expired + 1 new = 6
    assert total >= 6, f"Expected at least 6 tokens (5 expired + 1 new), got {total}"

    # Count expired tokens specifically
    result = await db_session.execute(
        select(func.count(RefreshToken.id)).where(
            RefreshToken.user_id == test_user.id,
            RefreshToken.expires_at < datetime.now(timezone.utc),
        )
    )
    expired_count = result.scalar()
    assert expired_count == 5, f"All 5 expired tokens should still exist, got {expired_count}"
