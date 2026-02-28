import pytest
import pytest_asyncio
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.models.imaging import ImagingSession, ImagingStatus
from app.core.security import hash_password


@pytest_asyncio.fixture
async def expert_user(db_session):
    user = User(
        username="expertissue",
        email="expertissue@example.com",
        hashed_password=hash_password("ExpertPass123!"),
        full_name="Expert Issue User",
        role=UserRole.EXPERT,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcissue",
        email="crcissue@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC Issue User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def issue_test_data(db_session, crc_user):
    project = Project(code="ISS001", name="Issue Test Project")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CTR001", name="Test Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id,
        project_id=project.id,
        screening_number="SCR-ISS-001",
    )
    db_session.add(subject)
    await db_session.flush()

    session = ImagingSession(
        subject_id=subject.id,
        project_id=project.id,
        center_id=center.id,
        visit_point="V1",
        imaging_type="CT",
        status=ImagingStatus.COMPLETED,
        uploaded_by=crc_user.id,
    )
    db_session.add(session)
    await db_session.commit()
    return project, center, subject, session


async def _get_token(client, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_expert_can_create_issue(client, expert_user, crc_user, issue_test_data):
    project, center, subject, session = issue_test_data
    token = await _get_token(client, "expertissue", "ExpertPass123!")
    response = await client.post(
        "/api/issues",
        json={
            "session_id": session.id,
            "description": "Image quality issue detected",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == session.id
    assert data["subject_id"] == subject.id
    assert data["project_id"] == project.id
    assert data["center_id"] == center.id
    assert data["visit_point"] == "V1"
    assert data["status"] == "pending"
    assert data["description"] == "Image quality issue detected"
    assert data["created_by"] == expert_user.id


@pytest.mark.asyncio
async def test_crc_cannot_create_issue(client, crc_user, issue_test_data):
    project, center, subject, session = issue_test_data
    token = await _get_token(client, "crcissue", "CrcPass123!")
    response = await client.post(
        "/api/issues",
        json={
            "session_id": session.id,
            "description": "Should not be allowed",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_issues_with_filters(client, expert_user, crc_user, issue_test_data):
    project, center, subject, session = issue_test_data
    token = await _get_token(client, "expertissue", "ExpertPass123!")

    # Create an issue first
    await client.post(
        "/api/issues",
        json={
            "session_id": session.id,
            "description": "Test issue for listing",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # List with project_id filter
    response = await client.get(
        f"/api/issues?project_id={project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
    assert data["items"][0]["project_id"] == project.id


@pytest.mark.asyncio
async def test_get_issue_detail_with_logs(client, expert_user, crc_user, issue_test_data):
    project, center, subject, session = issue_test_data
    token = await _get_token(client, "expertissue", "ExpertPass123!")

    # Create an issue
    create_resp = await client.post(
        "/api/issues",
        json={
            "session_id": session.id,
            "description": "Detail test issue",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    issue_id = create_resp.json()["id"]

    # Get detail
    response = await client.get(
        f"/api/issues/{issue_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == issue_id
    assert data["description"] == "Detail test issue"
    assert "logs" in data
    assert len(data["logs"]) >= 1
    assert data["logs"][0]["action"] == "create"


@pytest.mark.asyncio
async def test_crc_can_process_issue(client, expert_user, crc_user, issue_test_data):
    project, center, subject, session = issue_test_data

    # Expert creates issue
    expert_token = await _get_token(client, "expertissue", "ExpertPass123!")
    create_resp = await client.post(
        "/api/issues",
        json={
            "session_id": session.id,
            "description": "Issue to process",
        },
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    issue_id = create_resp.json()["id"]

    # CRC processes issue
    crc_token = await _get_token(client, "crcissue", "CrcPass123!")
    response = await client.put(
        f"/api/issues/{issue_id}/process",
        json={"content": "Processing feedback from CRC"},
        headers={"Authorization": f"Bearer {crc_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reviewing"
