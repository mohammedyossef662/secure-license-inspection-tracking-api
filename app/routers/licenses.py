"""License endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import select

from app.auth.dependencies import AdminUser, CurrentUser, DbDep
from app.core.pagination import PaginationDep, paginate
from app.core.text import contains_pattern
from app.core.time import utc_today, utcnow
from app.models.enums import LicenseStatus, LicenseType
from app.models.facility import Facility
from app.models.license import License
from app.schemas.common import Page
from app.schemas.license import LicenseCreate, LicenseRead, LicenseUpdate
from app.services.audit import AuditAction, record_audit

router = APIRouter(prefix="/licenses", tags=["Licenses"])


def _base_query():
    return (
        select(License)
        .join(Facility)
        .where(License.is_deleted.is_(False), Facility.is_deleted.is_(False))
    )


def _get_license_or_404(db: DbDep, license_id: int) -> License:
    license_obj = db.scalar(_base_query().where(License.id == license_id))
    if license_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found.")
    return license_obj


@router.get("", response_model=Page[LicenseRead], summary="List licenses")
def list_licenses(
    db: DbDep,
    pagination: PaginationDep,
    _user: CurrentUser,
    facility_id: Annotated[int | None, Query(ge=1)] = None,
    license_status: Annotated[LicenseStatus | None, Query(alias="status")] = None,
    license_type: Annotated[LicenseType | None, Query(alias="type")] = None,
    expired: bool | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> dict:
    stmt = _base_query()
    if facility_id is not None:
        stmt = stmt.where(License.facility_id == facility_id)
    if license_status is not None:
        stmt = stmt.where(License.status == license_status)
    if license_type is not None:
        stmt = stmt.where(License.type == license_type)
    if expired is True:
        stmt = stmt.where(License.expiry_date < utc_today())
    elif expired is False:
        stmt = stmt.where(License.expiry_date >= utc_today())
    if search:
        stmt = stmt.where(License.license_number.ilike(contains_pattern(search), escape="\\"))
    stmt = stmt.order_by(License.created_at.desc(), License.id.desc())
    return paginate(db, stmt, pagination)


@router.post(
    "",
    response_model=LicenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a license (Admin only)",
)
def create_license(
    payload: LicenseCreate,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> License:
    facility = db.get(Facility, payload.facility_id)
    if facility is None or facility.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found.",
        )
    existing = db.scalar(select(License.id).where(License.license_number == payload.license_number))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="License number is already in use.",
        )
    license_obj = License(
        facility_id=facility.id,
        license_number=payload.license_number,
        type=payload.type,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        status=payload.status,
    )
    db.add(license_obj)
    db.flush()
    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.LICENSE_CREATED,
        entity="license",
        entity_id=license_obj.id,
        details=f"facility_id={facility.id}",
    )
    db.commit()
    db.refresh(license_obj)
    return license_obj


@router.get("/{license_id}", response_model=LicenseRead, summary="Read a license")
def read_license(license_id: int, db: DbDep, _user: CurrentUser) -> License:
    return _get_license_or_404(db, license_id)


@router.put("/{license_id}", response_model=LicenseRead, summary="Update a license (Admin only)")
def update_license(
    license_id: int,
    payload: LicenseUpdate,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> License:
    license_obj = _get_license_or_404(db, license_id)
    data = payload.model_dump(exclude_unset=True)
    updates = {key: value for key, value in data.items() if value is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one non-null field must be provided.",
        )

    new_issue_date = updates.get("issue_date", license_obj.issue_date)
    new_expiry_date = updates.get("expiry_date", license_obj.expiry_date)
    if new_expiry_date <= new_issue_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="expiry_date must be after issue_date.",
        )

    if "license_number" in updates and updates["license_number"] != license_obj.license_number:
        duplicate = db.scalar(
            select(License.id).where(
                License.license_number == updates["license_number"],
                License.id != license_obj.id,
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="License number is already in use.",
            )
    for key, value in updates.items():
        setattr(license_obj, key, value)

    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.LICENSE_UPDATED,
        entity="license",
        entity_id=license_obj.id,
        details=f"fields={','.join(sorted(updates))}",
    )
    db.commit()
    db.refresh(license_obj)
    return license_obj


@router.delete(
    "/{license_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete (revoke) a license (Admin only)",
)
def delete_license(
    license_id: int,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> Response:
    license_obj = _get_license_or_404(db, license_id)
    license_obj.is_deleted = True
    license_obj.deleted_at = utcnow()
    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.LICENSE_DELETED,
        entity="license",
        entity_id=license_obj.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
