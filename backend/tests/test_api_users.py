import pytest
import pytest_asyncio
from app.models.user import User, UserRole
from app.core.security import hash_password


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcuser",
        email="crc@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC User",
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
async def test_admin_create_user(client, admin_user):
    token = await _get_token(client, "admin", "AdminPass123!")
    response = await client.post(
        "/api/users",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "full_name": "New User",
            "role": "crc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert data["role"] == "crc"


@pytest.mark.asyncio
async def test_admin_list_users(client, admin_user):
    token = await _get_token(client, "admin", "AdminPass123!")
    response = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_non_admin_cannot_create_user(client, crc_user):
    token = await _get_token(client, "crcuser", "CrcPass123!")
    response = await client.post(
        "/api/users",
        json={
            "username": "another",
            "email": "another@example.com",
            "password": "Pass123!",
            "full_name": "Another User",
            "role": "crc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_user(client, admin_user, crc_user):
    token = await _get_token(client, "admin", "AdminPass123!")
    response = await client.put(
        f"/api/users/{crc_user.id}",
        json={"full_name": "Updated Name", "phone": "1234567890"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["phone"] == "1234567890"


@pytest.mark.asyncio
async def test_change_own_password(client, crc_user):
    token = await _get_token(client, "crcuser", "CrcPass123!")
    response = await client.put(
        "/api/users/me/password",
        json={"old_password": "CrcPass123!", "new_password": "NewCrcPass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"
