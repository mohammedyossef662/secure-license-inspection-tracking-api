"""ORM models.

Importing this package registers every model with the declarative base, which
Alembic needs in order to build metadata.
"""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.enums import (
    FacilityStatus,
    InspectionResult,
    LicenseStatus,
    LicenseType,
    UserRole,
)
from app.models.facility import Facility
from app.models.inspection import Inspection
from app.models.license import License
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "Facility",
    "FacilityStatus",
    "Inspection",
    "InspectionResult",
    "License",
    "LicenseStatus",
    "LicenseType",
    "User",
    "UserRole",
]
