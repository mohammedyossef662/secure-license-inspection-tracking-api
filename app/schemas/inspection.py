"""Inspection schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, PositiveInt, model_validator

from app.core.time import utc_today
from app.models.enums import InspectionResult
from app.schemas.common import Notes, ORMModel, StrictModel


def _not_in_future(value: date) -> date:
    if value > utc_today():
        raise ValueError("inspection_date cannot be in the future")
    return value


InspectionDate = Annotated[date, AfterValidator(_not_in_future)]


class InspectionCreate(StrictModel):
    facility_id: PositiveInt
    inspector_id: PositiveInt | None = None
    inspection_date: InspectionDate
    result: InspectionResult
    notes: Notes | None = None


class InspectionUpdate(StrictModel):
    inspection_date: InspectionDate | None = None
    result: InspectionResult | None = None
    notes: Notes | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> InspectionUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class InspectionRead(ORMModel):
    id: int
    facility_id: int
    inspector_id: int
    inspector_username: str | None
    inspection_date: date
    result: InspectionResult
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
