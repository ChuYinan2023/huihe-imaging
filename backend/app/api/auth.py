import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, hash_token,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    access_token = create_access_token(user.id, user.role.value, user.token_version)
    refresh_token_str, jti, family_id = create_refresh_token(user.id, user.token_version)
    csrf_token = secrets.token_urlsafe(32)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        jti=jti,
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )

    return {
        "access_token": access_token,
        "csrf_token": csrf_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value,
            "email": user.email,
        },
    }


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    try:
        payload = decode_token(token, audience="refresh")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload["jti"]
    family_id = payload["fid"]
    user_id = int(payload["sub"])

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    rt = result.scalar_one_or_none()

    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not found")

    if rt.used:
        # Token reuse detected - invalidate entire family
        from sqlalchemy import update
        await db.execute(
            update(RefreshToken).where(RefreshToken.family_id == family_id).values(used=True)
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token reuse detected")

    rt.used = True

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active or user.token_version != payload.get("tv"):
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    new_access = create_access_token(user.id, user.role.value, user.token_version)
    new_refresh, new_jti, same_family = create_refresh_token(
        user.id, user.token_version, family_id=family_id
    )

    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh),
        jti=new_jti,
        family_id=same_family,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_rt)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )

    return {"access_token": new_access}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
        "email": user.email,
        "phone": user.phone,
    }
