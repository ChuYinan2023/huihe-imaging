import hashlib
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import check_permission, Permission
from app.models.user import User, UserRole
from app.models.imaging import ImagingSession, ImagingFile, ImagingStatus
from app.services.state_machine import ImagingFSM
from app.services.upload_service import validate_file, generate_stored_filename
from app.services.audit_service import AuditService
from app.api.deps import get_current_user, get_client_ip, get_user_agent

router = APIRouter(prefix="/api/imaging", tags=["imaging"])


class CreateSessionRequest(BaseModel):
    project_id: int
    center_id: int
    subject_id: int
    visit_point: str
    imaging_type: str


def _session_response(session: ImagingSession) -> dict:
    return {
        "id": session.id,
        "project_id": session.project_id,
        "center_id": session.center_id,
        "subject_id": session.subject_id,
        "visit_point": session.visit_point,
        "imaging_type": session.imaging_type,
        "status": session.status.value if session.status else None,
        "uploaded_by": session.uploaded_by,
        "file_hash": session.file_hash,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def _file_response(f: ImagingFile) -> dict:
    return {
        "id": f.id,
        "session_id": f.session_id,
        "original_filename": f.original_filename,
        "stored_filename": f.stored_filename,
        "file_path": f.file_path,
        "anonymized_path": f.anonymized_path,
        "file_size": f.file_size,
        "file_hash": f.file_hash,
        "mime_type": f.mime_type,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.UPLOAD_IMAGING):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    session = ImagingSession(
        project_id=body.project_id,
        center_id=body.center_id,
        subject_id=body.subject_id,
        visit_point=body.visit_point,
        imaging_type=body.imaging_type,
        uploaded_by=current_user.id,
        status=ImagingStatus.UPLOADING,
    )
    db.add(session)
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="create_session",
        resource_type="imaging_session",
        resource_id=str(session.id),
        after_value={"project_id": body.project_id, "subject_id": body.subject_id},
    )

    await db.commit()
    await db.refresh(session)
    return _session_response(session)


@router.post("/sessions/{session_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    session_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.UPLOAD_IMAGING):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Verify session exists and belongs to user
    result = await db.execute(
        select(ImagingSession).where(ImagingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.status != ImagingStatus.UPLOADING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not in uploading status",
        )

    # Validate file
    if not file.filename or not validate_file(file.filename, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type",
        )

    # Save to tmp directory first
    stored_name = generate_stored_filename(file.filename)
    tmp_dir = settings.STORAGE_ROOT / settings.STORAGE_TMP_DIR
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / stored_name

    # Stream file to tmp in chunks — never load entire file into memory
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    sha256 = hashlib.sha256()
    file_size = 0
    try:
        with open(tmp_path, "wb") as f:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit",
                    )
                sha256.update(chunk)
                f.write(chunk)
    except HTTPException:
        tmp_path.unlink(missing_ok=True)
        raise

    file_hash = sha256.hexdigest()

    # Atomic move to originals
    originals_dir = settings.STORAGE_ROOT / settings.STORAGE_ORIGINALS_DIR
    originals_dir.mkdir(parents=True, exist_ok=True)
    final_path = originals_dir / stored_name
    os.replace(str(tmp_path), str(final_path))

    # Store file metadata
    relative_path = f"{settings.STORAGE_ORIGINALS_DIR}/{stored_name}"
    imaging_file = ImagingFile(
        session_id=session_id,
        original_filename=file.filename,
        stored_filename=stored_name,
        file_path=relative_path,
        file_size=file_size,
        file_hash=file_hash,
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(imaging_file)

    # Update session hash
    session.file_hash = file_hash

    # Transition status: UPLOADING -> ANONYMIZING
    new_status = ImagingFSM.transition(session.status, ImagingStatus.ANONYMIZING)
    session.status = new_status

    # Audit log
    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="upload_file",
        resource_type="imaging_file",
        resource_id=str(session_id),
        after_value={"filename": file.filename, "size": file_size, "hash": file_hash},
    )

    await db.commit()
    await db.refresh(imaging_file)
    return _file_response(imaging_file)


@router.get("")
async def list_sessions(
    project_id: int | None = None,
    center_id: int | None = None,
    subject_id: int | None = None,
    status_filter: str | None = None,
    visit_point: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_IMAGING):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    query = select(ImagingSession)
    count_query = select(func.count(ImagingSession.id))

    if project_id is not None:
        query = query.where(ImagingSession.project_id == project_id)
        count_query = count_query.where(ImagingSession.project_id == project_id)
    if center_id is not None:
        query = query.where(ImagingSession.center_id == center_id)
        count_query = count_query.where(ImagingSession.center_id == center_id)
    if subject_id is not None:
        query = query.where(ImagingSession.subject_id == subject_id)
        count_query = count_query.where(ImagingSession.subject_id == subject_id)
    if status_filter is not None:
        query = query.where(ImagingSession.status == status_filter)
        count_query = count_query.where(ImagingSession.status == status_filter)
    if visit_point is not None:
        query = query.where(ImagingSession.visit_point == visit_point)
        count_query = count_query.where(ImagingSession.visit_point == visit_point)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(ImagingSession.id.desc()).offset(offset).limit(page_size)
    )
    sessions = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_session_response(s) for s in sessions],
    }


@router.get("/by-subject")
async def sessions_by_subject(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_IMAGING):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    query = select(ImagingSession)
    if project_id is not None:
        query = query.where(ImagingSession.project_id == project_id)

    result = await db.execute(query.order_by(ImagingSession.subject_id, ImagingSession.id))
    sessions = result.scalars().all()

    grouped: dict[int, list[dict]] = {}
    for s in sessions:
        grouped.setdefault(s.subject_id, []).append(_session_response(s))

    return {"subjects": grouped}


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_IMAGING):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(
        select(ImagingSession).where(ImagingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    files_result = await db.execute(
        select(ImagingFile).where(ImagingFile.session_id == session_id).order_by(ImagingFile.id)
    )
    files = files_result.scalars().all()

    resp = _session_response(session)
    resp["files"] = [_file_response(f) for f in files]
    return resp
