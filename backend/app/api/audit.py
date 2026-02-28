from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import check_permission, Permission
from app.models.user import User
from app.models.audit import AuditLog
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _audit_response(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "operator_id": log.operator_id,
        "ip": log.ip,
        "user_agent": log.user_agent,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "before_value": log.before_value,
        "after_value": log.after_value,
    }


@router.get("")
async def list_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    operator_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.VIEW_AUDIT_LOG):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action is not None:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if operator_id is not None:
        query = query.where(AuditLog.operator_id == operator_id)
        count_query = count_query.where(AuditLog.operator_id == operator_id)
    if date_from is not None:
        query = query.where(AuditLog.timestamp >= date_from)
        count_query = count_query.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        query = query.where(AuditLog.timestamp <= date_to)
        count_query = count_query.where(AuditLog.timestamp <= date_to)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AuditLog.id.desc()).offset(offset).limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_audit_response(log) for log in logs],
    }
