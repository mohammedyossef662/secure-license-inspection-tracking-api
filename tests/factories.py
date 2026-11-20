"""ORM object factories used by tests."""

from __future__ import annotations

import itertools
from datetime import date, timedelta

from app.core.time import utc_today
from app.models import (
    Facility,
    FacilityStatus,
    Inspection,
    InspectionResult,
    License,
    LicenseStatus,
    LicenseType,
    User,
    UserRole,
)
from sqlalchemy.orm import Session

_counter = itertools.count(1)


def create_user(
    db: Session,
    username: str,
    role: str,
    password_hash: str,
    full_name: str | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        full_name=full_name,
        role=UserRole(role),
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    return user


def create_facility(
    db: Session,
    name: str = "Acme Materials",
    registration_number: str | None = None,
    status: FacilityStatus = FacilityStatus.ACTIVE,
    address: str = "12 Industrial Road, Cairo",
) -> Facility:
    number = registration_number or f"REG-{next(_counter):04d}"
    facility = Facility(
        name=name,
        registration_number=number,
        address=address,
        status=status,
    )
    db.add(facility)
    db.commit()
    return facility


def create_license(
    db: Session,
    facility: Facility,
    license_number: str | None = None,
    license_type: LicenseType = LicenseType.OPERATING,
    issue_date: date | None = None,
    expiry_date: date | None = None,
    status: LicenseStatus = LicenseStatus.ACTIVE,
) -> License:
    today = utc_today()
    license_obj = License(
        facility_id=facility.id,
        license_number=license_number or f"LIC-{next(_counter):04d}",
        type=license_type,
        issue_date=issue_date or today - timedelta(days=30),
        expiry_date=expiry_date or today + timedelta(days=365),
        status=status,
    )
    db.add(license_obj)
    db.commit()
    return license_obj


def create_inspection(
    db: Session,
    facility: Facility,
    inspector: User,
    inspection_date: date | None = None,
    result: InspectionResult = InspectionResult.COMPLIANT,
    notes: str | None = None,
) -> Inspection:
    inspection = Inspection(
        facility_id=facility.id,
        inspector_id=inspector.id,
        inspection_date=inspection_date or utc_today(),
        result=result,
        notes=notes,
    )
    db.add(inspection)
    db.commit()
    return inspection
