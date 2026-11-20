"""Authentication and role-based authorization dependencies."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.tokens import decode_access_token
from app.core.config import Settings
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.services.audit import AuditAction, write_audit_event

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False,
    description="JWT access token obtained from POST /auth/login.",
)


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbDep = Annotated[Session, Depends(get_db)]


def _unauthorized(detail: str = "Invalid authentication credentials.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbDep,
    settings: SettingsDep,
) -> User:
    if not token:
        raise _unauthorized("Not authenticated.")
    try:
        payload = decode_access_token(token, settings)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise _unauthorized() from exc

    revoked = request.app.state.token_revocation
    jti = payload.get("jti")
    if isinstance(jti, str) and revoked.is_revoked(jti):
        raise _unauthorized("Token has been revoked.")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole):
    """Build a dependency that enforces function-level authorization (RBAC)."""

    def dependency(request: Request, user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            write_audit_event(
                request,
                user_id=user.id,
                action=AuditAction.ACCESS_DENIED,
                entity="authorization",
                details=(
                    f"path={request.url.path};"
                    f"required={','.join(role.value for role in allowed_roles)}"
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
StaffUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INSPECTOR))]
