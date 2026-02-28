import pytest
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.models.imaging import ImagingSession
from app.models.issue import Issue, IssueStatus, IssueLog
from app.models.report import Report
from sqlalchemy import select


async def _create_session_fixtures(db_session):
    """Helper to create user, project, center, subject, and imaging session."""
    user = User(
        username="issueuser",
        email="issueuser@test.com",
        hashed_password="hashed",
        full_name="Issue User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(code="ISS-PROJ", name="Issue Project")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CTR-I1", name="Issue Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id, project_id=project.id, screening_number="SCR-I01"
    )
    db_session.add(subject)
    await db_session.flush()

    session = ImagingSession(
        subject_id=subject.id,
        project_id=project.id,
        center_id=center.id,
        visit_point="V1",
        imaging_type="MRI",
        uploaded_by=user.id,
    )
    db_session.add(session)
    await db_session.flush()

    return user, project, center, subject, session


@pytest.mark.asyncio
async def test_create_issue_and_log(db_session):
    user, project, center, subject, session = await _create_session_fixtures(db_session)

    issue = Issue(
        session_id=session.id,
        subject_id=subject.id,
        project_id=project.id,
        center_id=center.id,
        visit_point="V1",
        description="Missing scan sequence",
        created_by=user.id,
    )
    db_session.add(issue)
    await db_session.flush()

    log = IssueLog(
        issue_id=issue.id,
        operator_id=user.id,
        action="create",
        content="Issue created",
        from_status=None,
        to_status="pending",
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(Issue).where(Issue.project_id == project.id)
    )
    saved_issue = result.scalar_one()
    assert saved_issue.status == IssueStatus.PENDING
    assert saved_issue.description == "Missing scan sequence"

    result = await db_session.execute(
        select(IssueLog).where(IssueLog.issue_id == issue.id)
    )
    saved_log = result.scalar_one()
    assert saved_log.action == "create"
    assert saved_log.to_status == "pending"


@pytest.mark.asyncio
async def test_issue_status_enum_values(db_session):
    assert IssueStatus.PENDING.value == "pending"
    assert IssueStatus.PROCESSING.value == "processing"
    assert IssueStatus.REVIEWING.value == "reviewing"
    assert IssueStatus.CLOSED.value == "closed"


@pytest.mark.asyncio
async def test_create_report(db_session):
    user, project, center, subject, session = await _create_session_fixtures(db_session)

    report = Report(
        session_id=session.id,
        subject_id=subject.id,
        project_id=project.id,
        file_path="/reports/report_001.pdf",
        uploaded_by=user.id,
        ai_summary="Normal findings",
    )
    db_session.add(report)
    await db_session.commit()

    result = await db_session.execute(
        select(Report).where(Report.project_id == project.id)
    )
    saved = result.scalar_one()
    assert saved.file_path == "/reports/report_001.pdf"
    assert saved.ai_summary == "Normal findings"
    assert saved.signed_file_path is None
    assert saved.issue_id is None
