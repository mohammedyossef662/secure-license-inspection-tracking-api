"""Inspection records."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import InspectionResult, enum_type

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.facility import Facility
    from app.models.user import User


class Inspection(TimestampMixin, Base):
    __tablename__ = "inspections"
    __table_args__ = (
        Index("ix_inspections_facility_date", "facility_id", "inspection_date"),
        Index("ix_inspections_inspector", "inspector_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    inspector_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    result: Mapped[InspectionResult] = mapped_column(
        enum_type(InspectionResult, "ck_inspections_result", 32), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    facility: Mapped[Facility] = relationship(back_populates="inspections", lazy="selectin")
    inspector: Mapped[User] = relationship(back_populates="inspections", lazy="selectin")

    @property
    def inspector_username(self) -> str | None:
        return self.inspector.username if self.inspector is not None else None
