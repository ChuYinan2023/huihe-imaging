from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import check_permission, Permission
from app.models.user import User
from app.models.imaging import ImagingSession
from app.models.issue import Issue, IssueStatus, IssueLog
from app.services.state_machine import IssueFSM, InvalidTransitionError
from app.services.audit_service import AuditService
from app.api.deps import get_current_user, get_client_ip, get_user_agent

router = APIRouter(prefix="/api/issues", tags=["issues"])


class CreateIssueRequest(BaseModel):
    session_id: int
    description: str


class ProcessIssueRequest(BaseModel):
    content: str


class ReviewIssueRequest(BaseModel):
    action: str  # "approve" or "reject"
    content: str | None = None


def _issue_response(issue: Issue) -> dict:
    return {
        "id": issue.id,
        "session_id": issue.session_id,
        "subject_id": issue.subject_id,
        "project_id": issue.project_id,
        "center_id": issue.center_id,
        "visit_point": issue.visit_point,
        "status": issue.status.value if issue.status else None,
        "description": issue.description,
        "created_by": issue.created_by,
        "assigned_to": issue.assigned_to,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }


def _issue_log_response(log: IssueLog) -> dict:
    return {
        "id": log.id,
        "issue_id": log.issue_id,
        "operator_id": log.operator_id,
        "action": log.action,
        "content": log.content,
        "from_status": log.from_status,
        "to_status": log.to_status,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_issue(
    body: CreateIssueRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.CREATE_ISSUE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Fetch session to auto-fill fields
    result = await db.execute(
        select(ImagingSession).where(ImagingSession.id == body.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imaging session not found")

    issue = Issue(
        session_id=session.id,
        subject_id=session.subject_id,
        project_id=session.project_id,
        center_id=session.center_id,
        visit_point=session.visit_point,
        description=body.description,
        status=IssueStatus.PENDING,
        created_by=current_user.id,
    )
    db.add(issue)
    await db.flush()

    # Create initial log entry
    log = IssueLog(
        issue_id=issue.id,
        operator_id=current_user.id,
        action="create",
        content=body.description,
        from_status=None,
        to_status=IssueStatus.PENDING.value,
    )
    db.add(log)

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="create_issue",
        resource_type="issue",
        resource_id=str(issue.id),
        after_value={"session_id": body.session_id, "description": body.description},
    )

    await db.commit()
    await db.refresh(issue)

    return _issue_response(issue)


@router.get("")
async def list_issues(
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
    if not check_permission(current_user.role, Permission.VIEW_ISSUES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    query = select(Issue)
    count_query = select(func.count(Issue.id))

    if project_id is not None:
        query = query.where(Issue.project_id == project_id)
        count_query = count_query.where(Issue.project_id == project_id)
    if center_id is not None:
        query = query.where(Issue.center_id == center_id)
        count_query = count_query.where(Issue.center_id == center_id)
    if subject_id is not None:
        query = query.where(Issue.subject_id == subject_id)
        count_query = count_query.where(Issue.subject_id == subject_id)
    if status_filter is not None:
        query = query.where(Issue.status == status_filter)
        count_query = count_query.where(Issue.status == status_filter)
    if visit_point is not None:
        query = query.where(Issue.visit_point == visit_point)
        count_query = count_query.where(Issue.visit_point == visit_point)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Issue.id.desc()).offset(offset).limit(page_size)
    )
    issues = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_issue_response(i) for i in issues],
    }


@router.get("/{issue_id}")
async def get_issue(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_ISSUES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    logs_result = await db.execute(
        select(IssueLog).where(IssueLog.issue_id == issue_id).order_by(IssueLog.id)
    )
    logs = logs_result.scalars().all()

    resp = _issue_response(issue)
    resp["logs"] = [_issue_log_response(log) for log in logs]
    return resp


@router.put("/{issue_id}/process")
async def process_issue(
    issue_id: int,
    body: ProcessIssueRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.PROCESS_ISSUE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    old_status = issue.status

    # FSM transition: pending -> processing
    try:
        if old_status == IssueStatus.PENDING:
            new_status = IssueFSM.transition(old_status, IssueStatus.PROCESSING)
            issue.status = new_status

            log1 = IssueLog(
                issue_id=issue.id,
                operator_id=current_user.id,
                action="process",
                content=body.content,
                from_status=old_status.value,
                to_status=new_status.value,
            )
            db.add(log1)

            # Then processing -> reviewing
            old_status2 = new_status
            new_status2 = IssueFSM.transition(old_status2, IssueStatus.REVIEWING)
            issue.status = new_status2

            log2 = IssueLog(
                issue_id=issue.id,
                operator_id=current_user.id,
                action="submit_review",
                content=body.content,
                from_status=old_status2.value,
                to_status=new_status2.value,
            )
            db.add(log2)
        elif old_status == IssueStatus.PROCESSING:
            new_status = IssueFSM.transition(old_status, IssueStatus.REVIEWING)
            issue.status = new_status

            log = IssueLog(
                issue_id=issue.id,
                operator_id=current_user.id,
                action="submit_review",
                content=body.content,
                from_status=old_status.value,
                to_status=new_status.value,
            )
            db.add(log)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot process issue in {old_status.value} status",
            )
    except InvalidTransitionError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {old_status.value}",
        )

    issue.assigned_to = current_user.id

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="process_issue",
        resource_type="issue",
        resource_id=str(issue_id),
        before_value={"status": old_status.value},
        after_value={"status": issue.status.value},
    )

    await db.commit()
    await db.refresh(issue)
    return _issue_response(issue)


@router.put("/{issue_id}/review")
async def review_issue(
    issue_id: int,
    body: ReviewIssueRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.REVIEW_ISSUE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if body.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'",
        )

    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    old_status = issue.status

    try:
        if body.action == "approve":
            new_status = IssueFSM.transition(old_status, IssueStatus.CLOSED)
        else:
            new_status = IssueFSM.transition(old_status, IssueStatus.PENDING)
    except InvalidTransitionError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {old_status.value}",
        )

    issue.status = new_status

    log = IssueLog(
        issue_id=issue.id,
        operator_id=current_user.id,
        action=f"review_{body.action}",
        content=body.content,
        from_status=old_status.value,
        to_status=new_status.value,
    )
    db.add(log)

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action=f"review_issue_{body.action}",
        resource_type="issue",
        resource_id=str(issue_id),
        before_value={"status": old_status.value},
        after_value={"status": new_status.value},
    )

    await db.commit()
    await db.refresh(issue)
    return _issue_response(issue)
