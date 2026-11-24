"""Audit log schemas."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    id: int
    user_id: int | None
    username: str | None
    action: str
    entity: str
    entity_id: int | None
    details: str | None
    ip_address: str | None
    timestamp: datetime
