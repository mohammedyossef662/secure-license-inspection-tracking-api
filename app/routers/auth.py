"""Authentication endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, DbDep, SettingsDep, oauth2_scheme
from app.auth.password import (
    hash_password,
    password_needs_rehash,
    verify_against_dummy,
    verify_password,
)
from app.auth.tokens import create_access_token, decode_access_token
from app.core.time import utcnow
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserRead
from app.services.audit import AuditAction, client_ip, record_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def parse_login_request(request: Request) -> LoginRequest:
    """Accept both JSON and OAuth2-style form bodies.

    JSON is the documented API format; form support keeps the Swagger UI
    "Authorize" button and standard OAuth2 password-flow clients working.
    """

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        form = await request.form()
        data: Any = {
            "username": form.get("username"),
            "password": form.get("password"),
        }
    else:
        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid request body.",
            ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid request body.",
        )
    try:
        return LoginRequest.model_validate(data)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current access token",
)
def logout(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    user: CurrentUser,
    request: Request,
) -> None:
    """Blacklist the presented access token until its original expiry."""

    if token is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token, request.app.state.settings)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if isinstance(jti, str) and isinstance(exp, (int, float)):
            revocation = request.app.state.token_revocation
            if revocation is not None:
                revocation.revoke(jti, datetime.fromtimestamp(float(exp), tz=UTC))
    except jwt.PyJWTError:
        # An already-invalid token needs no revocation bookkeeping.
        pass


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate and obtain a JWT access token",
    responses={
        401: {"description": "Invalid credentials or inactive account"},
        429: {"description": "Too many failed login attempts"},
    },
)
def login(
    request: Request,
    credentials: Annotated[LoginRequest, Depends(parse_login_request)],
    settings: SettingsDep,
    db: DbDep,
) -> LoginResponse:
    ip = client_ip(request)
    limiter = request.app.state.login_limiter
    scopes = limiter.scopes(ip, credentials.username)

    retry_after = limiter.retry_after(scopes)
    if retry_after:
        record_audit(
            db,
            request,
            user_id=None,
            action=AuditAction.LOGIN_BLOCKED,
            entity="auth",
            details="reason=rate_limited",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(select(User).where(User.username == credentials.username))

    if user is None:
        verify_against_dummy(credentials.password)
        limiter.record_failure(scopes)
        record_audit(
            db,
            request,
            user_id=None,
            action=AuditAction.LOGIN_FAILED,
            entity="auth",
            details="reason=invalid_credentials",
        )
        db.commit()
        raise _invalid_credentials()

    if not verify_password(credentials.password, user.password_hash):
        limiter.record_failure(scopes)
        record_audit(
            db,
            request,
            user_id=user.id,
            action=AuditAction.LOGIN_FAILED,
            entity="auth",
            entity_id=user.id,
            details="reason=invalid_credentials",
        )
        db.commit()
        raise _invalid_credentials()

    if not user.is_active:
        limiter.record_failure(scopes)
        record_audit(
            db,
            request,
            user_id=user.id,
            action=AuditAction.LOGIN_FAILED,
            entity="auth",
            entity_id=user.id,
            details="reason=inactive_account",
        )
        db.commit()
        raise _invalid_credentials()

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(credentials.password)
    user.last_login_at = utcnow()

    # A successful login clears the account counter, but not the wider per-IP
    # failure history, which protects against username spraying.
    limiter.reset([scopes[0]])

    token, expires_in = create_access_token(user, settings)
    record_audit(
        db,
        request,
        user_id=user.id,
        action=AuditAction.LOGIN_SUCCESS,
        entity="auth",
        entity_id=user.id,
    )
    db.commit()
    return LoginResponse(
        access_token=token,
        token_type="bearer",  # noqa: S106 - fixed token type, not a secret
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )
