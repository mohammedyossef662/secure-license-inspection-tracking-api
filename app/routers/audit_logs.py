"""Audit log read endpoint (Admin only)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.auth.dependencies import AdminUser, DbDep
from app.core.pagination import PaginationDep, paginate
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import Page
from app.services.audit import AuditAction

router = APIRouter(prefix="/audit-logs", tags=["Audit logs"])


@router.get("", response_model=Page[AuditLogRead], summary="List audit log entries (Admin only)")
def list_audit_logs(
    db: DbDep,
    pagination: PaginationDep,
    _admin: AdminUser,
    action: AuditAction | None = None,
    entity: Annotated[str | None, Query(max_length=32)] = None,
    entity_id: Annotated[int | None, Query(ge=1)] = None,
    user_id: Annotated[int | None, Query(ge=1)] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must be on or before date_to.",
        )
    stmt = select(AuditLog)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action.value)
    if entity is not None:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.timestamp <= date_to)
    stmt = stmt.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    return paginate(db, stmt, pagination)
