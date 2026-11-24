"""License schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import PositiveInt, model_validator

from app.models.enums import LicenseStatus, LicenseType
from app.schemas.common import Code, ORMModel, StrictModel


def _validate_date_order(issue_date: date, expiry_date: date) -> None:
    if expiry_date <= issue_date:
        raise ValueError("expiry_date must be after issue_date")


class LicenseCreate(StrictModel):
    facility_id: PositiveInt
    license_number: Code
    type: LicenseType
    issue_date: date
    expiry_date: date
    status: LicenseStatus = LicenseStatus.ACTIVE

    @model_validator(mode="after")
    def _dates_in_order(self) -> LicenseCreate:
        _validate_date_order(self.issue_date, self.expiry_date)
        return self


class LicenseUpdate(StrictModel):
    license_number: Code | None = None
    type: LicenseType | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    status: LicenseStatus | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> LicenseUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if self.issue_date is not None and self.expiry_date is not None:
            _validate_date_order(self.issue_date, self.expiry_date)
        return self


class LicenseRead(ORMModel):
    id: int
    facility_id: int
    license_number: str
    type: LicenseType
    issue_date: date
    expiry_date: date
    status: LicenseStatus
    is_expired: bool
    created_at: datetime
    updated_at: datetime | None
