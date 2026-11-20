"""Facility endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select, update

from app.auth.dependencies import AdminUser, CurrentUser, DbDep
from app.core.pagination import PaginationDep, paginate
from app.core.text import contains_pattern
from app.core.time import utc_today, utcnow
from app.models.enums import FacilityStatus, LicenseStatus
from app.models.facility import Facility
from app.models.license import License
from app.schemas.common import Page
from app.schemas.facility import FacilityCreate, FacilityRead, FacilityUpdate
from app.services.audit import AuditAction, record_audit

router = APIRouter(prefix="/facilities", tags=["Facilities"])


def _get_facility_or_404(db: DbDep, facility_id: int) -> Facility:
    facility = db.get(Facility, facility_id)
    if facility is None or facility.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    return facility


@router.get("", response_model=Page[FacilityRead], summary="List facilities")
def list_facilities(
    db: DbDep,
    pagination: PaginationDep,
    _user: CurrentUser,
    search: Annotated[str | None, Query(max_length=100)] = None,
    facility_status: Annotated[FacilityStatus | None, Query(alias="status")] = None,
) -> dict:
    stmt = select(Facility).where(Facility.is_deleted.is_(False))
    if search:
        pattern = contains_pattern(search)
        stmt = stmt.where(
            or_(
                Facility.name.ilike(pattern, escape="\\"),
                Facility.registration_number.ilike(pattern, escape="\\"),
            )
        )
    if facility_status is not None:
        stmt = stmt.where(Facility.status == facility_status)
    stmt = stmt.order_by(Facility.created_at.desc(), Facility.id.desc())
    return paginate(db, stmt, pagination)


@router.post(
    "",
    response_model=FacilityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a facility (Admin only)",
)
def create_facility(
    payload: FacilityCreate,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> Facility:
    existing = db.scalar(
        select(Facility.id).where(Facility.registration_number == payload.registration_number)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration number is already in use.",
        )
    facility = Facility(
        name=payload.name,
        registration_number=payload.registration_number,
        address=payload.address,
        status=payload.status,
    )
    db.add(facility)
    db.flush()
    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.FACILITY_CREATED,
        entity="facility",
        entity_id=facility.id,
    )
    db.commit()
    db.refresh(facility)
    return facility


@router.get("/{facility_id}", response_model=FacilityRead, summary="Read a facility")
def read_facility(facility_id: int, db: DbDep, _user: CurrentUser) -> Facility:
    return _get_facility_or_404(db, facility_id)


@router.put("/{facility_id}", response_model=FacilityRead, summary="Update a facility (Admin only)")
def update_facility(
    facility_id: int,
    payload: FacilityUpdate,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> Facility:
    facility = _get_facility_or_404(db, facility_id)
    data = payload.model_dump(exclude_unset=True)
    updates = {key: value for key, value in data.items() if value is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one non-null field must be provided.",
        )

    if (
        "registration_number" in updates
        and updates["registration_number"] != facility.registration_number
    ):
        duplicate = db.scalar(
            select(Facility.id).where(
                Facility.registration_number == updates["registration_number"],
                Facility.id != facility.id,
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration number is already in use.",
            )
    for key, value in updates.items():
        setattr(facility, key, value)

    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.FACILITY_UPDATED,
        entity="facility",
        entity_id=facility.id,
        details=f"fields={','.join(sorted(updates))}",
    )
    db.commit()
    db.refresh(facility)
    return facility


@router.delete(
    "/{facility_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a facility (Admin only)",
)
def delete_facility(
    facility_id: int,
    request: Request,
    db: DbDep,
    admin: AdminUser,
) -> Response:
    facility = _get_facility_or_404(db, facility_id)

    active_license = db.scalar(
        select(License.id)
        .where(
            License.facility_id == facility.id,
            License.is_deleted.is_(False),
            License.status == LicenseStatus.ACTIVE,
            License.expiry_date >= utc_today(),
        )
        .limit(1)
    )
    if active_license is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Facility has active licenses and cannot be deleted.",
        )

    now = utcnow()
    license_count = int(
        db.scalar(
            select(func.count())
            .select_from(License)
            .where(License.facility_id == facility.id, License.is_deleted.is_(False))
        )
        or 0
    )
    # Soft delete preserves the audit trail and historical inspections.
    facility.is_deleted = True
    facility.deleted_at = now
    facility.status = FacilityStatus.CLOSED
    if license_count:
        db.execute(
            update(License)
            .where(License.facility_id == facility.id, License.is_deleted.is_(False))
            .values(is_deleted=True, deleted_at=now)
            .execution_options(synchronize_session=False)
        )
    record_audit(
        db,
        request,
        user_id=admin.id,
        action=AuditAction.FACILITY_DELETED,
        entity="facility",
        entity_id=facility.id,
        details=f"cascaded_licenses={license_count}",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
