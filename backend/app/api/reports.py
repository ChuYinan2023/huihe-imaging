import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import check_permission, Permission
from app.models.user import User
from app.models.imaging import ImagingSession
from app.models.report import Report
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _report_response(report: Report) -> dict:
    return {
        "id": report.id,
        "session_id": report.session_id,
        "subject_id": report.subject_id,
        "project_id": report.project_id,
        "issue_id": report.issue_id,
        "file_path": report.file_path,
        "signed_file_path": report.signed_file_path,
        "ai_summary": report.ai_summary,
        "uploaded_by": report.uploaded_by,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_report(
    session_id: int = Form(...),
    issue_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.UPLOAD_REPORT):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Verify session exists
    result = await db.execute(
        select(ImagingSession).where(ImagingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imaging session not found")

    # Save file
    reports_dir = settings.STORAGE_ROOT / settings.STORAGE_REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    stored_name = f"report_{session_id}_{file_hash}.pdf"
    file_path = reports_dir / stored_name
    file_path.write_bytes(content)

    relative_path = f"{settings.STORAGE_REPORTS_DIR}/{stored_name}"

    report = Report(
        session_id=session.id,
        subject_id=session.subject_id,
        project_id=session.project_id,
        issue_id=issue_id,
        file_path=relative_path,
        uploaded_by=current_user.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return _report_response(report)


@router.get("")
async def list_reports(
    project_id: int | None = None,
    subject_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_REPORTS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    query = select(Report)
    count_query = select(func.count(Report.id))

    if project_id is not None:
        query = query.where(Report.project_id == project_id)
        count_query = count_query.where(Report.project_id == project_id)
    if subject_id is not None:
        query = query.where(Report.subject_id == subject_id)
        count_query = count_query.where(Report.subject_id == subject_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Report.id.desc()).offset(offset).limit(page_size)
    )
    reports = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_report_response(r) for r in reports],
    }


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_REPORTS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return _report_response(report)


@router.post("/{report_id}/sign")
async def sign_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.UPLOAD_REPORT):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not current_user.signature_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no signature uploaded",
        )

    pdf_path = settings.STORAGE_ROOT / report.file_path
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report PDF file not found on disk",
        )

    signature_path = Path(current_user.signature_path)
    if not signature_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signature file not found",
        )

    from app.services.signature_service import compose_signature

    signed_name = f"signed_{report.id}_{pdf_path.name}"
    signed_dir = settings.STORAGE_ROOT / settings.STORAGE_REPORTS_DIR / "signed"
    signed_path = signed_dir / signed_name
    compose_signature(pdf_path, signature_path, signed_path)

    relative_signed = f"{settings.STORAGE_REPORTS_DIR}/signed/{signed_name}"
    report.signed_file_path = relative_signed
    await db.commit()
    await db.refresh(report)

    return _report_response(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_REPORTS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Use signed version if available
    file_rel_path = report.signed_file_path or report.file_path
    file_path = settings.STORAGE_ROOT / file_rel_path

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on disk",
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/pdf",
    )
