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


@pytest_asyncio.fixture
async def cra_user(db_session):
    user = User(
        username="crauser",
        email="cra@example.com",
        hashed_password=hash_password("CraPass123!"),
        full_name="CRA User",
        role=UserRole.CRA,
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
async def test_admin_create_project(client, admin_user):
    token = await _get_token(client, "admin", "AdminPass123!")
    response = await client.post(
        "/api/projects",
        json={"code": "PROJ001", "name": "Test Project", "description": "A test project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "PROJ001"
    assert data["name"] == "Test Project"


@pytest.mark.asyncio
async def test_non_admin_pm_cannot_create_project(client, crc_user):
    token = await _get_token(client, "crcuser", "CrcPass123!")
    response = await client.post(
        "/api/projects",
        json={"code": "PROJ002", "name": "Another Project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_projects(client, admin_user):
    token = await _get_token(client, "admin", "AdminPass123!")
    # Create a project first
    await client.post(
        "/api/projects",
        json={"code": "PROJ003", "name": "List Test Project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_add_center_to_project(client, admin_user):
    token = await _get_token(client, "admin", "AdminPass123!")
    # Create project
    proj_resp = await client.post(
        "/api/projects",
        json={"code": "PROJ004", "name": "Center Test Project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    project_id = proj_resp.json()["id"]

    # Add center
    response = await client.post(
        f"/api/projects/{project_id}/centers",
        json={"code": "CTR001", "name": "Test Center"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "CTR001"
    assert data["project_id"] == project_id


@pytest.mark.asyncio
async def test_add_subject_to_center(client, admin_user):
    token = await _get_token(client, "admin", "AdminPass123!")
    # Create project
    proj_resp = await client.post(
        "/api/projects",
        json={"code": "PROJ005", "name": "Subject Test Project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    project_id = proj_resp.json()["id"]

    # Add center
    center_resp = await client.post(
        f"/api/projects/{project_id}/centers",
        json={"code": "CTR002", "name": "Subject Test Center"},
        headers={"Authorization": f"Bearer {token}"},
    )
    center_id = center_resp.json()["id"]

    # Add subject
    response = await client.post(
        f"/api/projects/{project_id}/centers/{center_id}/subjects",
        json={"screening_number": "SCR-001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["screening_number"] == "SCR-001"
    assert data["center_id"] == center_id
    assert data["project_id"] == project_id
