"""Audit-log writing helpers."""

from __future__ import annotations

import logging
from enum import StrEnum

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditAction(StrEnum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_BLOCKED = "login_blocked"
    ACCESS_DENIED = "access_denied"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
    PROFILE_UPDATED = "profile_updated"
    FACILITY_CREATED = "facility_created"
    FACILITY_UPDATED = "facility_updated"
    FACILITY_DELETED = "facility_deleted"
    LICENSE_CREATED = "license_created"
    LICENSE_UPDATED = "license_updated"
    LICENSE_DELETED = "license_deleted"
    INSPECTION_CREATED = "inspection_created"
    INSPECTION_UPDATED = "inspection_updated"


def client_ip(request: Request) -> str:
    """Return the client address, honouring proxy headers only when trusted."""

    settings: Settings = request.app.state.settings
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:45]
    if request.client is not None:
        return request.client.host[:45]
    return "unknown"


def _clean_details(details: str | None) -> str | None:
    if details is None:
        return None
    return details.replace("\r", " ").replace("\n", " ")[:255]


def record_audit(
    db: Session,
    request: Request,
    *,
    user_id: int | None,
    action: AuditAction | str,
    entity: str,
    entity_id: int | None = None,
    details: str | None = None,
) -> AuditLog:
    """Add an audit entry to the caller's transaction (no commit)."""

    entry = AuditLog(
        user_id=user_id,
        action=action.value if isinstance(action, AuditAction) else action,
        entity=entity[:32],
        entity_id=entity_id,
        details=_clean_details(details),
        ip_address=client_ip(request),
    )
    db.add(entry)
    return entry


def write_audit_event(
    request: Request,
    *,
    user_id: int | None,
    action: AuditAction | str,
    entity: str,
    entity_id: int | None = None,
    details: str | None = None,
) -> None:
    """Persist an audit entry in an isolated transaction.

    Used for failed logins and authorization denials, where the main request is
    going to raise and its session is rolled back.
    """

    factory = request.app.state.session_factory
    db: Session = factory()
    try:
        record_audit(
            db,
            request,
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to persist audit event %s", action)
    finally:
        db.close()
