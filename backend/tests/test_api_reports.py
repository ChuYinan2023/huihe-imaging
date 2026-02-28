import io
import pytest
import pytest_asyncio
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.models.imaging import ImagingSession, ImagingStatus
from app.core.security import hash_password


@pytest_asyncio.fixture
async def expert_user(db_session):
    user = User(
        username="expertreport",
        email="expertreport@example.com",
        hashed_password=hash_password("ExpertPass123!"),
        full_name="Expert Report User",
        role=UserRole.EXPERT,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def crc_user(db_session):
    user = User(
        username="crcreport",
        email="crcreport@example.com",
        hashed_password=hash_password("CrcPass123!"),
        full_name="CRC Report User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def report_test_data(db_session, crc_user):
    project = Project(code="RPT001", name="Report Test Project")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CTR001", name="Test Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id,
        project_id=project.id,
        screening_number="SCR-RPT-001",
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


def _make_pdf_bytes() -> bytes:
    """Create a minimal valid PDF for testing."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n195\n%%EOF\n"
    )


@pytest.mark.asyncio
async def test_expert_can_upload_report(client, expert_user, crc_user, report_test_data):
    project, center, subject, session = report_test_data
    token = await _get_token(client, "expertreport", "ExpertPass123!")

    pdf_content = _make_pdf_bytes()
    response = await client.post(
        "/api/reports/upload",
        data={"session_id": str(session.id)},
        files={"file": ("test_report.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == session.id
    assert data["subject_id"] == subject.id
    assert data["project_id"] == project.id
    assert data["uploaded_by"] == expert_user.id
    assert "reports/" in data["file_path"]


@pytest.mark.asyncio
async def test_list_reports_with_filters(client, expert_user, crc_user, report_test_data):
    project, center, subject, session = report_test_data
    token = await _get_token(client, "expertreport", "ExpertPass123!")

    # Upload a report first
    pdf_content = _make_pdf_bytes()
    await client.post(
        "/api/reports/upload",
        data={"session_id": str(session.id)},
        files={"file": ("test_report.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )

    # List with project filter
    response = await client.get(
        f"/api/reports?project_id={project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
    assert data["items"][0]["project_id"] == project.id


@pytest.mark.asyncio
async def test_get_report_detail(client, expert_user, crc_user, report_test_data):
    project, center, subject, session = report_test_data
    token = await _get_token(client, "expertreport", "ExpertPass123!")

    # Upload a report
    pdf_content = _make_pdf_bytes()
    upload_resp = await client.post(
        "/api/reports/upload",
        data={"session_id": str(session.id)},
        files={"file": ("test_report.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    report_id = upload_resp.json()["id"]

    # Get detail
    response = await client.get(
        f"/api/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == report_id
    assert data["session_id"] == session.id
