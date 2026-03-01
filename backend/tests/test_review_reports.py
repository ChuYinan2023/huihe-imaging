"""
Review Issue Verification Tests — Reports & Services Module

Covers:
  Issue #5:  report upload has no file size limit
  Issue #6:  project listing not filtered by user role/assignment
  Issue #11: PROCESSING status never persisted (skipped to REVIEWING)
  Issue #13: validate_file redundant content_type check logic
  Issue #16: DICOM UID generation deterministic + salt-dependent
  Issue #17: signature overlay hardcoded A4 page size
  Issue #18: sign_report uses UPLOAD_REPORT permission (no SIGN_REPORT exists)
"""

import inspect
import io

import pytest
import pytest_asyncio
from sqlalchemy import select, func

from app.core.security import hash_password
from app.core.permissions import Permission, ROLE_PERMISSIONS
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.models.imaging import ImagingSession, ImagingStatus
from app.models.issue import Issue, IssueStatus, IssueLog
from app.services.upload_service import validate_file
from app.services.dicom_service import generate_uid
from app.services.signature_service import compose_signature


@pytest_asyncio.fixture
async def expert_user(db_session):
    user = User(
        username="expertreportrev",
        email="expertreportrev@example.com",
        hashed_password=hash_password("ExpertPass123!"),
        full_name="Expert Report Review",
        role=UserRole.EXPERT,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcreportrev",
        email="crcreportrev@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC Report Review",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        username="adminreportrev",
        email="adminreportrev@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin Report Review",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def report_test_data(db_session, expert_user):
    """Creates Project > Center > Subject > ImagingSession for report tests."""
    project = Project(code="RPTREV01", name="Report Review Project")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="RPTC01", name="Report Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id,
        project_id=project.id,
        screening_number="SCR-RPTREV-001",
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
        uploaded_by=expert_user.id,
    )
    db_session.add(session)
    await db_session.commit()
    return project, center, subject, session


@pytest_asyncio.fixture
async def issue_test_data(db_session, expert_user, report_test_data):
    """Creates an Issue in PENDING status for issue-flow tests."""
    project, center, subject, session = report_test_data
    issue = Issue(
        session_id=session.id,
        subject_id=subject.id,
        project_id=project.id,
        center_id=center.id,
        visit_point="V1",
        description="Test issue for review",
        status=IssueStatus.PENDING,
        created_by=expert_user.id,
    )
    db_session.add(issue)
    await db_session.flush()

    log = IssueLog(
        issue_id=issue.id,
        operator_id=expert_user.id,
        action="create",
        content="Test issue for review",
        from_status=None,
        to_status=IssueStatus.PENDING.value,
    )
    db_session.add(log)
    await db_session.commit()
    return issue


async def _get_token(client, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #5: report upload has no file size limit")
async def test_issue5_report_upload_no_size_limit(
    client, db_session, expert_user, report_test_data
):
    """Uploading a very large PDF should be rejected with 413.
    CURRENT: No size check — any size is accepted."""
    project, center, subject, session = report_test_data
    token = await _get_token(client, "expertreportrev", "ExpertPass123!")

    # Create a ~2MB fake PDF (small enough for test, but tests the check)
    large_content = b"%PDF-1.4\n" + b"x" * (2 * 1024 * 1024)

    response = await client.post(
        "/api/reports/upload",
        files={"file": ("large_report.pdf", io.BytesIO(large_content), "application/pdf")},
        data={"session_id": str(session.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    # The upload should enforce a size limit (e.g., MAX_FILE_SIZE_MB)
    # CURRENT: Returns 201 regardless of size
    assert response.status_code == 413, (
        f"Expected 413 for oversized upload, got {response.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Review Issue #6: project listing not filtered by user role/assignment")
async def test_issue6_non_admin_sees_all_projects(
    client, db_session, admin_user, crc_user
):
    """Non-admin users should only see projects they're assigned to.
    CURRENT: All users see all projects regardless of assignment."""
    token_admin = await _get_token(client, "adminreportrev", "AdminPass123!")

    # Admin creates 3 projects
    for i in range(3):
        await client.post(
            "/api/projects",
            json={"code": f"FILT{i:02d}", "name": f"Filter Test {i}"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )

    # CRC user lists projects (should only see assigned ones)
    token_crc = await _get_token(client, "crcreportrev", "CrcPass123!")
    response = await client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {token_crc}"},
    )
    assert response.status_code == 200
    data = response.json()

    # CRC is not assigned to any project, so should see 0
    # CURRENT: Sees all projects
    assert data["total"] == 0, (
        f"CRC with no assignments should see 0 projects, got {data['total']}"
    )


@pytest.mark.asyncio
async def test_issue11_processing_status_never_persisted(
    client, db_session, crc_user, expert_user, issue_test_data
):
    """Documents that PROCESSING status is skipped — issue goes directly
    from PENDING to REVIEWING when processed."""
    issue = issue_test_data
    assert issue.status == IssueStatus.PENDING

    token = await _get_token(client, "crcreportrev", "CrcPass123!")
    response = await client.put(
        f"/api/issues/{issue.id}/process",
        json={"content": "Processing this issue"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    # The final status is REVIEWING, not PROCESSING
    assert data["status"] == "reviewing", (
        f"Expected 'reviewing' after process, got '{data['status']}'"
    )


@pytest.mark.asyncio
async def test_issue11_double_log_entries_from_pending(
    client, db_session, crc_user, expert_user, issue_test_data
):
    """Documents that processing from PENDING creates 2 extra log entries
    (pending->processing + processing->reviewing), totaling 3 with creation."""
    issue = issue_test_data

    token = await _get_token(client, "crcreportrev", "CrcPass123!")
    await client.put(
        f"/api/issues/{issue.id}/process",
        json={"content": "Processing this issue"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get issue detail with logs
    response = await client.get(
        f"/api/issues/{issue.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    logs = data["logs"]
    # 1: create (from fixture), 2: process, 3: submit_review
    assert len(logs) == 3, f"Expected 3 log entries, got {len(logs)}"

    actions = [log["action"] for log in logs]
    assert actions == ["create", "process", "submit_review"], (
        f"Expected ['create', 'process', 'submit_review'], got {actions}"
    )


def test_issue13_validate_file_dcm_octet_stream_passes():
    """validate_file should accept .dcm with application/octet-stream."""
    assert validate_file("scan.dcm", "application/octet-stream") is True


def test_issue13_validate_file_exe_rejected():
    """validate_file should reject .exe files."""
    assert validate_file("malware.exe", "application/octet-stream") is False


def test_issue16_uid_deterministic():
    """generate_uid with same input and salt produces the same output."""
    uid1 = generate_uid("1.2.840.10008.1.1", "test-salt")
    uid2 = generate_uid("1.2.840.10008.1.1", "test-salt")
    assert uid1 == uid2
    assert uid1.startswith("2.25.")


def test_issue16_uid_different_salt():
    """generate_uid with different salts produces different UIDs."""
    uid1 = generate_uid("1.2.840.10008.1.1", "salt-A")
    uid2 = generate_uid("1.2.840.10008.1.1", "salt-B")
    assert uid1 != uid2


def test_issue17_signature_hardcoded_a4():
    """Documents that compose_signature uses hardcoded A4 page size
    and fixed coordinate values."""
    source = inspect.getsource(compose_signature)
    assert "A4" in source, "compose_signature should reference A4 page size"
    # Check for hardcoded coordinates (400, 50) and dimensions (120, 60)
    assert "400" in source, "Hardcoded x-coordinate 400"
    assert "50" in source, "Hardcoded y-coordinate 50"
    assert "120" in source, "Hardcoded width 120"
    assert "60" in source, "Hardcoded height 60"


def test_issue18_sign_uses_upload_permission():
    """Documents that no SIGN_REPORT permission exists — sign_report endpoint
    reuses UPLOAD_REPORT permission instead."""
    all_permissions = {p.value for p in Permission}
    assert "sign_report" not in all_permissions, (
        "There should be no 'sign_report' permission"
    )
    assert "upload_report" in all_permissions, (
        "UPLOAD_REPORT permission should exist"
    )

    # Verify sign_report endpoint uses UPLOAD_REPORT by checking source
    from app.api import reports as reports_module
    sign_source = inspect.getsource(reports_module.sign_report)
    assert "UPLOAD_REPORT" in sign_source, (
        "sign_report endpoint uses UPLOAD_REPORT permission"
    )
