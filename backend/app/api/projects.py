from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import check_permission, Permission
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    code: str
    name: str
    description: str | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class CreateCenterRequest(BaseModel):
    code: str
    name: str


class CreateSubjectRequest(BaseModel):
    screening_number: str


def _project_response(project: Project) -> dict:
    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "status": project.status,
        "description": project.description,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def _center_response(center: Center) -> dict:
    return {
        "id": center.id,
        "project_id": center.project_id,
        "code": center.code,
        "name": center.name,
        "created_at": center.created_at.isoformat() if center.created_at else None,
    }


def _subject_response(subject: Subject) -> dict:
    return {
        "id": subject.id,
        "center_id": subject.center_id,
        "project_id": subject.project_id,
        "screening_number": subject.screening_number,
        "created_at": subject.created_at.isoformat() if subject.created_at else None,
    }


def _can_manage_projects(role: UserRole) -> bool:
    return check_permission(role, Permission.MANAGE_PROJECTS)


def _can_manage_subjects(role: UserRole) -> bool:
    """Admin, PM, and CRC can add subjects."""
    return role in (UserRole.ADMIN, UserRole.PM, UserRole.CRC)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_projects(current_user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    existing = await db.execute(select(Project).where(Project.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project code already exists")

    project = Project(
        code=body.code,
        name=body.name,
        description=body.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _project_response(project)


@router.get("")
async def list_projects(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_result = await db.execute(select(func.count(Project.id)))
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Project).order_by(Project.id).offset(offset).limit(page_size)
    )
    projects = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_project_response(p) for p in projects],
    }


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    body: UpdateProjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_projects(current_user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return _project_response(project)


@router.post("/{project_id}/centers", status_code=status.HTTP_201_CREATED)
async def add_center(
    project_id: int,
    body: CreateCenterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_projects(current_user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing = await db.execute(
        select(Center).where(Center.project_id == project_id, Center.code == body.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Center code already exists in project")

    center = Center(
        project_id=project_id,
        code=body.code,
        name=body.name,
    )
    db.add(center)
    await db.commit()
    await db.refresh(center)
    return _center_response(center)


@router.get("/{project_id}/centers")
async def list_centers(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    centers_result = await db.execute(
        select(Center).where(Center.project_id == project_id).order_by(Center.id)
    )
    centers = centers_result.scalars().all()
    return {"items": [_center_response(c) for c in centers]}


@router.post("/{project_id}/centers/{center_id}/subjects", status_code=status.HTTP_201_CREATED)
async def add_subject(
    project_id: int,
    center_id: int,
    body: CreateSubjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_manage_subjects(current_user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Verify center belongs to project
    center_result = await db.execute(
        select(Center).where(Center.id == center_id, Center.project_id == project_id)
    )
    if not center_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Center not found in project")

    existing = await db.execute(
        select(Subject).where(
            Subject.project_id == project_id,
            Subject.screening_number == body.screening_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Screening number already exists in project")

    subject = Subject(
        center_id=center_id,
        project_id=project_id,
        screening_number=body.screening_number,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return _subject_response(subject)


@router.get("/{project_id}/subjects")
async def list_subjects(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    subjects_result = await db.execute(
        select(Subject).where(Subject.project_id == project_id).order_by(Subject.id)
    )
    subjects = subjects_result.scalars().all()
    return {"items": [_subject_response(s) for s in subjects]}
