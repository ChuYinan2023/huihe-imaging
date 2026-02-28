import pytest
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.models.imaging import ImagingSession, ImagingFile, ImagingStatus, AnonymizationLog
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_imaging_session(db_session):
    user = User(
        username="uploader",
        email="uploader@test.com",
        hashed_password="hashed",
        full_name="Uploader",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(code="IMG-PROJ", name="Imaging Project")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CTR-01", name="Center 1")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id, project_id=project.id, screening_number="SCR-100"
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
    await db_session.commit()

    result = await db_session.execute(
        select(ImagingSession).where(ImagingSession.project_id == project.id)
    )
    saved = result.scalar_one()
    assert saved.visit_point == "V1"
    assert saved.imaging_type == "MRI"
    assert saved.status == ImagingStatus.UPLOADING
    assert saved.created_at is not None


@pytest.mark.asyncio
async def test_imaging_status_enum_values(db_session):
    assert ImagingStatus.UPLOADING.value == "uploading"
    assert ImagingStatus.ANONYMIZING.value == "anonymizing"
    assert ImagingStatus.COMPLETED.value == "completed"
    assert ImagingStatus.UPLOAD_FAILED.value == "upload_failed"
    assert ImagingStatus.ANONYMIZE_FAILED.value == "anonymize_failed"
    assert ImagingStatus.REJECTED.value == "rejected"


@pytest.mark.asyncio
async def test_create_imaging_file_and_anonymization_log(db_session):
    user = User(
        username="uploader2",
        email="uploader2@test.com",
        hashed_password="hashed",
        full_name="Uploader 2",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(code="IMG-PROJ2", name="Imaging Project 2")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CTR-02", name="Center 2")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id, project_id=project.id, screening_number="SCR-200"
    )
    db_session.add(subject)
    await db_session.flush()

    session = ImagingSession(
        subject_id=subject.id,
        project_id=project.id,
        center_id=center.id,
        visit_point="V2",
        imaging_type="CT",
        uploaded_by=user.id,
    )
    db_session.add(session)
    await db_session.flush()

    img_file = ImagingFile(
        session_id=session.id,
        original_filename="scan.dcm",
        stored_filename="abc123.dcm",
        file_path="/storage/abc123.dcm",
        file_size=1024000,
        file_hash="a" * 64,
        mime_type="application/dicom",
    )
    db_session.add(img_file)
    await db_session.flush()

    anon_log = AnonymizationLog(
        session_id=session.id,
        file_id=img_file.id,
        original_tag_hash="b" * 64,
        strategy_version="1.0",
        private_tags_removed=5,
        uid_mappings={"1.2.3": "4.5.6"},
    )
    db_session.add(anon_log)
    await db_session.commit()

    result = await db_session.execute(
        select(ImagingFile).where(ImagingFile.session_id == session.id)
    )
    saved_file = result.scalar_one()
    assert saved_file.original_filename == "scan.dcm"
    assert saved_file.file_size == 1024000

    result = await db_session.execute(
        select(AnonymizationLog).where(AnonymizationLog.session_id == session.id)
    )
    saved_log = result.scalar_one()
    assert saved_log.private_tags_removed == 5
    assert saved_log.strategy_version == "1.0"
