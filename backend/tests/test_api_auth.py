import pytest
import pytest_asyncio
from app.models.user import User, UserRole
from app.core.security import hash_password


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Test User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    response = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "csrf_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    response = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "pass",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client, test_user):
    login = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "TestPass123!",
    })
    token = login.json()["access_token"]
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "crc"


@pytest.mark.asyncio
async def test_get_me_without_token(client):
    response = await client.get("/api/auth/me")
    assert response.status_code in (401, 403)
