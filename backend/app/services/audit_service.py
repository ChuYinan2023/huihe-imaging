import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog

SENSITIVE_FIELDS = {"phone", "mobile", "id_card", "id_number", "identity"}


def sanitize_value(field_name: str, value: str) -> str:
    if field_name in SENSITIVE_FIELDS:
        if re.match(r"^\d{11}$", value):  # phone
            return f"{value[:3]}****{value[-4:]}"
        if re.match(r"^\d{17}[\dXx]$", value):  # id card
            return f"{value[:3]}{'*' * 11}{value[-4:]}"
    return value


def sanitize_dict(data: dict | None) -> str | None:
    if data is None:
        return None
    sanitized = {}
    for k, v in data.items():
        if isinstance(v, str):
            sanitized[k] = sanitize_value(k, v)
        else:
            sanitized[k] = v
    return json.dumps(sanitized, ensure_ascii=False)


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        operator_id: int,
        ip: str,
        user_agent: str | None,
        action: str,
        resource_type: str,
        resource_id: str,
        before_value: dict | None = None,
        after_value: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            operator_id=operator_id,
            ip=ip,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_value=sanitize_dict(before_value),
            after_value=sanitize_dict(after_value),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
