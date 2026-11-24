"""Facility schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from app.models.enums import FacilityStatus
from app.schemas.common import Address, Code, FacilityName, ORMModel, StrictModel


class FacilityCreate(StrictModel):
    name: FacilityName
    registration_number: Code
    address: Address
    status: FacilityStatus = FacilityStatus.ACTIVE


class FacilityUpdate(StrictModel):
    name: FacilityName | None = None
    registration_number: Code | None = None
    address: Address | None = None
    status: FacilityStatus | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> FacilityUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class FacilityRead(ORMModel):
    id: int
    name: str
    registration_number: str
    address: str
    status: FacilityStatus
    created_at: datetime
    updated_at: datetime | None
