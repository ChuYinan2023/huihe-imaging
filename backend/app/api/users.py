from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.core.permissions import check_permission, Permission
from app.models.user import User, UserRole
from app.services.audit_service import AuditService
from app.api.deps import get_current_user, get_client_ip, get_user_agent

router = APIRouter(prefix="/api/users", tags=["users"])

DEFAULT_PASSWORD = "Huihe@2024"


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: UserRole
    phone: str | None = None


class UpdateUserRequest(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    phone: str | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "phone": user.phone,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        phone=body.phone,
    )
    db.add(user)
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="create_user",
        resource_type="user",
        resource_id=str(user.id),
        after_value={"username": body.username, "role": body.role.value, "phone": body.phone},
    )

    await db.commit()
    await db.refresh(user)
    return _user_response(user)


@router.get("")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(User.id).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_user_response(u) for u in users],
    }


# This must be before /{user_id} routes to avoid route conflicts
@router.put("/me/password")
async def change_own_password(
    body: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    current_user.hashed_password = hash_password(body.new_password)
    current_user.token_version += 1

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="change_password",
        resource_type="user",
        resource_id=str(current_user.id),
    )

    await db.commit()
    return {"message": "Password changed successfully"}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)
    before = {k: getattr(user, k) for k in update_data}
    for field, value in update_data.items():
        setattr(user, field, value)

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="update_user",
        resource_type="user",
        resource_id=str(user_id),
        before_value={k: str(v) if v is not None else None for k, v in before.items()},
        after_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )

    await db.commit()
    await db.refresh(user)
    return _user_response(user)


@router.put("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.hashed_password = hash_password(DEFAULT_PASSWORD)
    user.token_version += 1

    audit = AuditService(db)
    await audit.log(
        operator_id=current_user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="reset_password",
        resource_type="user",
        resource_id=str(user_id),
    )

    await db.commit()
    return {"message": "Password reset to default"}
