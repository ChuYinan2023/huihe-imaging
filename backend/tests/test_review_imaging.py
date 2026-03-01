"""
Review Issue Verification Tests — Imaging Module

Covers:
  Issue #4:  upload does not trigger anonymization Celery task
  Issue #10: session ownership not verified on upload
  Issue #12: imaging file response leaks internal file paths
"""

import io

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.models.imaging import ImagingSession, ImagingStatus


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcimgrev",
        email="crcimgrev@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC Imaging Review",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def second_crc_user(db_session):
    user = User(
        username="crcimgrev2",
        email="crcimgrev2@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="Second CRC Imaging Review",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def project_with_session(db_session, crc_user):
    """Creates Project > Center > Subject > ImagingSession (UPLOADING)."""
    project = Project(code="IMGREV01", name="Imaging Review Project")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CREV01", name="Review Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id,
        project_id=project.id,
        screening_number="SCR-IMGREV-001",
    )
    db_session.add(subject)
    await db_session.flush()

    session = ImagingSession(
        subject_id=subject.id,
        project_id=project.id,
        center_id=center.id,
        visit_point="V1",
        imaging_type="CT",
        status=ImagingStatus.UPLOADING,
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


def _make_dcm_bytes() -> bytes:
    """Create minimal bytes that pass DICOM extension validation."""
    return b"\x00" * 128 + b"DICM" + b"\x00" * 100


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #4: upload does not dispatch Celery anonymize task")
async def test_issue4_upload_does_not_dispatch_anonymize_task(
    client, db_session, crc_user, project_with_session, monkeypatch
):
    """After file upload, anonymize_session.delay() should be called.
    CURRENT: No Celery task is dispatched — status stays ANONYMIZING forever."""
    project, center, subject, session = project_with_session

    # Track whether delay() is called
    calls = []

    # Monkeypatch the task module — imaging.py doesn't import it yet, so this
    # tests the expectation that it SHOULD import and call it.
    try:
        import app.tasks.imaging_tasks as tasks_mod
        original_delay = getattr(tasks_mod, "anonymize_session", None)

        class FakeTask:
            def delay(self, *args, **kwargs):
                calls.append({"args": args, "kwargs": kwargs})

        monkeypatch.setattr(tasks_mod, "anonymize_session", FakeTask(), raising=False)
    except ImportError:
        pass

    token = await _get_token(client, "crcimgrev", "CrcPass123!")
    response = await client.post(
        f"/api/imaging/sessions/{session.id}/upload",
        files={"file": ("test.dcm", io.BytesIO(_make_dcm_bytes()), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    # The real assertion: delay() should have been called
    assert len(calls) > 0, "anonymize_session.delay() was never called after upload"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #10: session ownership not verified on upload")
async def test_issue10_another_user_can_upload_to_foreign_session(
    client, db_session, crc_user, second_crc_user, project_with_session
):
    """User B should NOT be able to upload to User A's session.
    CURRENT: Any user with UPLOAD_IMAGING permission can upload to any session."""
    project, center, subject, session = project_with_session
    # session.uploaded_by == crc_user.id

    # Login as second_crc_user (not the session owner)
    token = await _get_token(client, "crcimgrev2", "CrcPass123!")
    response = await client.post(
        f"/api/imaging/sessions/{session.id}/upload",
        files={"file": ("test.dcm", io.BytesIO(_make_dcm_bytes()), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Expected: 403 Forbidden (not the session owner)
    assert response.status_code == 403, (
        f"Expected 403 for non-owner upload, got {response.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #12: file response leaks internal storage paths")
async def test_issue12_file_response_leaks_internal_paths(
    client, db_session, crc_user, project_with_session
):
    """API response should NOT expose file_path or anonymized_path.
    CURRENT: Both internal paths are included in the response."""
    project, center, subject, session = project_with_session
    token = await _get_token(client, "crcimgrev", "CrcPass123!")

    # Upload a file
    upload_resp = await client.post(
        f"/api/imaging/sessions/{session.id}/upload",
        files={"file": ("test.dcm", io.BytesIO(_make_dcm_bytes()), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_resp.status_code == 201

    # Get session detail to see file info
    detail_resp = await client.get(
        f"/api/imaging/{session.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert "files" in data
    assert len(data["files"]) > 0

    file_data = data["files"][0]
    # These internal fields should NOT be exposed
    assert "file_path" not in file_data, "file_path leaks internal storage path"
    assert "anonymized_path" not in file_data, "anonymized_path leaks internal storage path"
