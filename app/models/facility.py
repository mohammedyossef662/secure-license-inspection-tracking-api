"""Facilities regulated by the authority."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import FacilityStatus, enum_type

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.inspection import Inspection
    from app.models.license import License


class Facility(TimestampMixin, Base):
    __tablename__ = "facilities"
    __table_args__ = (Index("ix_facilities_status_deleted", "status", "is_deleted"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[FacilityStatus] = mapped_column(
        enum_type(FacilityStatus, "ck_facilities_status", 20),
        nullable=False,
        default=FacilityStatus.ACTIVE,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    licenses: Mapped[list[License]] = relationship(back_populates="facility")
    inspections: Mapped[list[Inspection]] = relationship(back_populates="facility")
