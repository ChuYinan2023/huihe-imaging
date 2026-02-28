import pytest
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject, ProjectUser
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_project_with_center_and_subject(db_session):
    project = Project(
        code="PROJ-001",
        name="Test Project",
        status="active",
        description="A test project",
    )
    db_session.add(project)
    await db_session.flush()

    center = Center(
        project_id=project.id,
        code="CTR-001",
        name="Test Center",
    )
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id,
        project_id=project.id,
        screening_number="SCR-001",
    )
    db_session.add(subject)
    await db_session.commit()

    result = await db_session.execute(select(Project).where(Project.code == "PROJ-001"))
    saved_project = result.scalar_one()
    assert saved_project.name == "Test Project"
    assert saved_project.status == "active"
    assert saved_project.created_at is not None

    result = await db_session.execute(select(Center).where(Center.project_id == project.id))
    saved_center = result.scalar_one()
    assert saved_center.code == "CTR-001"
    assert saved_center.project_id == project.id

    result = await db_session.execute(select(Subject).where(Subject.project_id == project.id))
    saved_subject = result.scalar_one()
    assert saved_subject.screening_number == "SCR-001"
    assert saved_subject.center_id == center.id


@pytest.mark.asyncio
async def test_project_user_association(db_session):
    user = User(
        username="projuser",
        email="projuser@test.com",
        hashed_password="hashed",
        full_name="Project User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(
        code="PROJ-002",
        name="Another Project",
    )
    db_session.add(project)
    await db_session.flush()

    pu = ProjectUser(
        user_id=user.id,
        project_id=project.id,
    )
    db_session.add(pu)
    await db_session.commit()

    result = await db_session.execute(
        select(ProjectUser).where(ProjectUser.user_id == user.id)
    )
    saved = result.scalar_one()
    assert saved.project_id == project.id
    assert saved.user_id == user.id
