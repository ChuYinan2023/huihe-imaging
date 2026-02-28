import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: int, role: str, token_version: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iss": settings.JWT_ISSUER,
        "aud": "access",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: int,
    token_version: int,
    family_id: str | None = None,
) -> tuple[str, str, str]:
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    fid = family_id or str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "tv": token_version,
        "iss": settings.JWT_ISSUER,
        "aud": "refresh",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "jti": jti,
        "fid": fid,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, fid


def decode_token(token: str, audience: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=audience,
        leeway=timedelta(seconds=settings.JWT_LEEWAY_SECONDS),
        options={"require": ["exp", "nbf", "iat", "iss", "aud"]},
    )
