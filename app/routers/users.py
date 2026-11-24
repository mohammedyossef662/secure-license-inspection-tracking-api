"""User administration and self-service profile endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import or_, select

from app.auth.dependencies import AdminUser, CurrentUser, DbDep
from app.auth.password import hash_password, verify_password
from app.core.pagination import PaginationDep, paginate
from app.core.text import contains_pattern
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import ProfileUpdate, UserAdminUpdate, UserCreate, UserRead
from app.services.audit import AuditAction, record_audit

router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_or_404(db: DbDep, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.get("/me", response_model=UserRead, summary="Read the current user")
def read_me(user: CurrentUser) -> User:
    return user


@router.put("/me", response_model=UserRead, summary="Update the current user's profile")
def update_me(
    payload: ProfileUpdate,
    request: Request,
    db: DbDep,
    user: CurrentUser,
) -> User:
    if payload.new_password is not None:
        current_password = payload.current_password or ""
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        user.password_hash = hash_password(payload.new_password)
    if "full_name" in payload.model_fields_set:
        user.full_name = payload.full_name

    record_audit(
        db,
        request,
        user_id=user.id,
        action=AuditAction.PROFILE_UPDATED,
        entity="user",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (Admin only)",
)
def create_user(
    payload: UserCreate,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> User:
    existing = db.scalar(select(User.id).where(User.username == payload.username))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already in use.",
        )
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.USER_CREATED,
        entity="user",
        entity_id=user.id,
        details=f"username={user.username};role={user.role.value}",
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=Page[UserRead], summary="List users (Admin only)")
def list_users(
    db: DbDep,
    pagination: PaginationDep,
    _admin: AdminUser,
    search: Annotated[str | None, Query(max_length=100)] = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> dict:
    stmt = select(User)
    if search:
        pattern = contains_pattern(search)
        stmt = stmt.where(
            or_(
                User.username.ilike(pattern, escape="\\"),
                User.full_name.ilike(pattern, escape="\\"),
            )
        )
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    stmt = stmt.order_by(User.created_at.desc(), User.id.desc())
    return paginate(db, stmt, pagination)


@router.get("/{user_id}", response_model=UserRead, summary="Read a user (Admin only)")
def read_user(user_id: int, db: DbDep, _admin: AdminUser) -> User:
    return _get_user_or_404(db, user_id)


@router.put("/{user_id}", response_model=UserRead, summary="Update a user (Admin only)")
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> User:
    user = _get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    new_role = payload.role if payload.role is not None else user.role
    new_is_active = payload.is_active if payload.is_active is not None else user.is_active

    if user.id == admin.id and (new_role != user.role or new_is_active is False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot change your own role or deactivate your own account.",
        )

    if "full_name" in data:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    changed = sorted(name for name in data if data[name] is not None or name == "full_name")
    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.USER_UPDATED,
        entity="user",
        entity_id=user.id,
        details=f"fields={','.join(changed)}",
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user (Admin only)",
)
def deactivate_user(
    user_id: int,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> Response:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot deactivate your own account.",
        )
    user = _get_user_or_404(db, user_id)
    if not user.is_active:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    user.is_active = False
    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.USER_DEACTIVATED,
        entity="user",
        entity_id=user.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
