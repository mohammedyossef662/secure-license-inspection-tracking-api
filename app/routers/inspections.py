"""Inspection endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, DbDep, StaffUser
from app.core.pagination import PaginationDep, paginate
from app.models.enums import InspectionResult, UserRole
from app.models.facility import Facility
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.common import Page
from app.schemas.inspection import InspectionCreate, InspectionRead, InspectionUpdate
from app.services.audit import AuditAction, record_audit, write_audit_event

router = APIRouter(prefix="/inspections", tags=["Inspections"])


def _get_inspection_or_404(db: DbDep, inspection_id: int) -> Inspection:
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found.",
        )
    return inspection


@router.get("", response_model=Page[InspectionRead], summary="List inspections")
def list_inspections(
    db: DbDep,
    pagination: PaginationDep,
    _user: CurrentUser,
    facility_id: Annotated[int | None, Query(ge=1)] = None,
    inspector_id: Annotated[int | None, Query(ge=1)] = None,
    result: InspectionResult | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must be on or before date_to.",
        )
    stmt = select(Inspection)
    if facility_id is not None:
        stmt = stmt.where(Inspection.facility_id == facility_id)
    if inspector_id is not None:
        stmt = stmt.where(Inspection.inspector_id == inspector_id)
    if result is not None:
        stmt = stmt.where(Inspection.result == result)
    if date_from is not None:
        stmt = stmt.where(Inspection.inspection_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Inspection.inspection_date <= date_to)
    stmt = stmt.order_by(Inspection.inspection_date.desc(), Inspection.id.desc())
    return paginate(db, stmt, pagination)


@router.post(
    "",
    response_model=InspectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record an inspection (Admin or Inspector)",
)
def create_inspection(
    payload: InspectionCreate,
    request: Request,
    db: DbDep,
    user: StaffUser,
) -> Inspection:
    facility = db.get(Facility, payload.facility_id)
    if facility is None or facility.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found.",
        )

    if user.role == UserRole.INSPECTOR:
        if payload.inspector_id is not None and payload.inspector_id != user.id:
            write_audit_event(
                request,
                user_id=user.id,
                action=AuditAction.ACCESS_DENIED,
                entity="inspection",
                details=f"attempted_inspector_id={payload.inspector_id}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inspectors can only record their own inspections.",
            )
        inspector = user
    else:
        if payload.inspector_id is None or payload.inspector_id == user.id:
            inspector = user
        else:
            inspector = db.get(User, payload.inspector_id)
            if (
                inspector is None
                or not inspector.is_active
                or inspector.role not in {UserRole.ADMIN, UserRole.INSPECTOR}
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Selected inspector is not an active inspector or admin.",
                )

    inspection = Inspection(
        facility=facility,
        inspector=inspector,
        inspection_date=payload.inspection_date,
        result=payload.result,
        notes=payload.notes,
    )
    db.add(inspection)
    db.flush()
    record_audit(
        db,
        request,
        user_id=user.id,
        action=AuditAction.INSPECTION_CREATED,
        entity="inspection",
        entity_id=inspection.id,
        details=f"facility_id={facility.id}",
    )
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("/{inspection_id}", response_model=InspectionRead, summary="Read an inspection")
def read_inspection(
    inspection_id: int,
    db: DbDep,
    _user: CurrentUser,
) -> Inspection:
    return _get_inspection_or_404(db, inspection_id)


@router.put(
    "/{inspection_id}",
    response_model=InspectionRead,
    summary="Update an inspection (Admin, or the owning Inspector)",
)
def update_inspection(
    inspection_id: int,
    payload: InspectionUpdate,
    request: Request,
    db: DbDep,
    user: CurrentUser,
) -> Inspection:
    inspection = _get_inspection_or_404(db, inspection_id)

    # BOLA / IDOR prevention: inspectors may only modify their own records.
    if user.role != UserRole.ADMIN and inspection.inspector_id != user.id:
        write_audit_event(
            request,
            user_id=user.id,
            action=AuditAction.ACCESS_DENIED,
            entity="inspection",
            entity_id=inspection.id,
            details="owner_check",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own inspections.",
        )

    if payload.inspection_date is not None:
        inspection.inspection_date = payload.inspection_date
    if payload.result is not None:
        inspection.result = payload.result
    if "notes" in payload.model_fields_set:
        inspection.notes = payload.notes

    record_audit(
        db,
        request,
        user_id=user.id,
        action=AuditAction.INSPECTION_UPDATED,
        entity="inspection",
        entity_id=inspection.id,
    )
    db.commit()
    db.refresh(inspection)
    return inspection
