"""Development / demo seed data for the Regulatory License & Inspection Tracking API.

Run with::

    python -m scripts.seed

The script is idempotent and creates a small demo dataset: an administrator,
inspectors and a viewer, plus one facility, license and inspection.

All credentials are development-only defaults; production deployments must use
real, strong credentials (see ``.env.example`` and ``docs/06-deployment.md``).
"""

from __future__ import annotations

from datetime import date, timedelta

from app.auth.password import hash_password
from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.time import utc_today
from app.models import (
    Base,
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
from sqlalchemy import select
from sqlalchemy.orm import Session

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "AdminPassword_123!"
INSPECTOR_USERNAME = "inspector_a"
INSPECTOR_PASSWORD = "InspectorPassword_123!"
VIEWER_USERNAME = "viewer_test"
VIEWER_PASSWORD = "ViewerPassword_123!"

FACILITY_NAME = "Nile Chemicals"
FACILITY_REGISTRATION = "REG-1000"


def _get_user(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def _ensure_user(
    db: Session,
    username: str,
    password: str,
    role: UserRole,
    full_name: str,
) -> User:
    user = _get_user(db, username)
    if user is not None:
        return user
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def seed() -> None:
    """Create the demo dataset in a single database transaction."""

    settings = get_settings()
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)

    with factory() as db:
        admin = _ensure_user(
            db, ADMIN_USERNAME, ADMIN_PASSWORD, UserRole.ADMIN, "System Administrator"
        )
        inspector = _ensure_user(
            db, INSPECTOR_USERNAME, INSPECTOR_PASSWORD, UserRole.INSPECTOR, "Inspector A"
        )
        _ensure_user(db, VIEWER_USERNAME, VIEWER_PASSWORD, UserRole.VIEWER, "Viewer Test")

        facility = db.scalar(
            select(Facility).where(Facility.registration_number == FACILITY_REGISTRATION)
        )
        if facility is None:
            facility = Facility(
                name=FACILITY_NAME,
                registration_number=FACILITY_REGISTRATION,
                address="12 Industrial Road, Cairo, Egypt",
                status=FacilityStatus.ACTIVE,
            )
            db.add(facility)
            db.flush()

        license_obj = db.scalar(select(License).where(License.facility_id == facility.id))
        if license_obj is None:
            db.add(
                License(
                    facility_id=facility.id,
                    license_number="LIC-1000",
                    type=LicenseType.OPERATING,
                    issue_date=utc_today() - timedelta(days=30),
                    expiry_date=utc_today() + timedelta(days=365),
                    status=LicenseStatus.ACTIVE,
                )
            )
            db.flush()

        inspection = db.scalar(select(Inspection).where(Inspection.facility_id == facility.id))
        if inspection is None:
            db.add(
                Inspection(
                    facility_id=facility.id,
                    inspector_id=inspector.id,
                    inspection_date=date.today(),
                    result=InspectionResult.COMPLIANT,
                    notes="Routine compliance inspection.",
                )
            )

        db.commit()
        print(f"Seeded admin={admin.username} inspector={inspector.username}")
        print(f"Seeded viewer={VIEWER_USERNAME} facility={facility.name}")


if __name__ == "__main__":
    seed()
