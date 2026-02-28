import pytest
import pytest_asyncio
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.models.imaging import ImagingSession, ImagingStatus
from app.core.security import hash_password


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcimaging",
        email="crcimaging@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC Imaging User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def cra_user(db_session):
    user = User(
        username="craimaging",
        email="craimaging@example.com",
        hashed_password=hash_password("CraPass123!"),
        full_name="CRA Imaging User",
        role=UserRole.CRA,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def project_with_subject(db_session):
    project = Project(code="IMG001", name="Imaging Test Project")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CTR001", name="Test Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id,
        project_id=project.id,
        screening_number="SCR-IMG-001",
    )
    db_session.add(subject)
    await db_session.commit()
    return project, center, subject


async def _get_token(client, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_crc_can_create_imaging_session(client, crc_user, project_with_subject):
    project, center, subject = project_with_subject
    token = await _get_token(client, "crcimaging", "CrcPass123!")
    response = await client.post(
        "/api/imaging/sessions",
        json={
            "project_id": project.id,
            "center_id": center.id,
            "subject_id": subject.id,
            "visit_point": "V1",
            "imaging_type": "CT",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project.id
    assert data["center_id"] == center.id
    assert data["subject_id"] == subject.id
    assert data["visit_point"] == "V1"
    assert data["imaging_type"] == "CT"
    assert data["status"] == "uploading"


@pytest.mark.asyncio
async def test_non_crc_cannot_create_imaging_session(client, cra_user, project_with_subject):
    project, center, subject = project_with_subject
    token = await _get_token(client, "craimaging", "CraPass123!")
    response = await client.post(
        "/api/imaging/sessions",
        json={
            "project_id": project.id,
            "center_id": center.id,
            "subject_id": subject.id,
            "visit_point": "V1",
            "imaging_type": "CT",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_imaging_sessions(client, crc_user, project_with_subject):
    project, center, subject = project_with_subject
    token = await _get_token(client, "crcimaging", "CrcPass123!")

    # Create a session first
    await client.post(
        "/api/imaging/sessions",
        json={
            "project_id": project.id,
            "center_id": center.id,
            "subject_id": subject.id,
            "visit_point": "V1",
            "imaging_type": "MRI",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # List sessions with project_id filter
    response = await client.get(
        f"/api/imaging?project_id={project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
    assert data["items"][0]["project_id"] == project.id


@pytest.mark.asyncio
async def test_get_session_detail(client, crc_user, project_with_subject):
    project, center, subject = project_with_subject
    token = await _get_token(client, "crcimaging", "CrcPass123!")

    # Create a session
    create_resp = await client.post(
        "/api/imaging/sessions",
        json={
            "project_id": project.id,
            "center_id": center.id,
            "subject_id": subject.id,
            "visit_point": "V2",
            "imaging_type": "PET",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = create_resp.json()["id"]

    # Get session detail
    response = await client.get(
        f"/api/imaging/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["imaging_type"] == "PET"
    assert "files" in data
