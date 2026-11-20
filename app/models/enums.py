"""Domain enumerations shared by models and schemas."""

from __future__ import annotations

from enum import Enum, StrEnum

from sqlalchemy import Enum as SAEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    INSPECTOR = "inspector"
    VIEWER = "viewer"


class FacilityStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class LicenseType(StrEnum):
    OPERATING = "operating"
    RADIATION = "radiation"
    TRANSPORT = "transport"
    STORAGE = "storage"
    WASTE_MANAGEMENT = "waste_management"
    DECOMMISSIONING = "decommissioning"


class LicenseStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"


class InspectionResult(StrEnum):
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    FOLLOW_UP_REQUIRED = "follow_up_required"


def enum_type(enum_cls: type[Enum], name: str, length: int = 32) -> SAEnum:
    """Return a portable, validated string enum column type.

    ``native_enum=False`` keeps MySQL from creating a rigid native ENUM type,
    which makes migrations simpler, while ``create_constraint=True`` still
    enforces the allowed values at the database level.
    """

    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
