import pytest
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from sqlalchemy import select
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_create_user(db_session):
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password="hashed",
        full_name="Admin User",
        role=UserRole.ADMIN,
        phone="13800001234",
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.username == "admin"))
    saved = result.scalar_one()
    assert saved.username == "admin"
    assert saved.role == UserRole.ADMIN
    assert saved.token_version == 1
    assert saved.is_active is True


@pytest.mark.asyncio
async def test_user_token_version_default(db_session):
    user = User(
        username="test",
        email="test@test.com",
        hashed_password="hashed",
        full_name="Test",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    assert user.token_version == 1


@pytest.mark.asyncio
async def test_create_refresh_token(db_session):
    user = User(
        username="user1",
        email="user1@test.com",
        hashed_password="hashed",
        full_name="User 1",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.flush()

    rt = RefreshToken(
        user_id=user.id,
        token_hash="a" * 64,
        jti="test-jti-123",
        family_id="test-family-123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(rt)
    await db_session.commit()

    result = await db_session.execute(select(RefreshToken).where(RefreshToken.jti == "test-jti-123"))
    saved = result.scalar_one()
    assert saved.user_id == user.id
    assert saved.used is False
    assert saved.family_id == "test-family-123"
