"""Licenses issued to facilities."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_today
from app.models.base import Base, TimestampMixin
from app.models.enums import LicenseStatus, LicenseType, enum_type

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.facility import Facility


class License(TimestampMixin, Base):
    __tablename__ = "licenses"
    __table_args__ = (
        CheckConstraint("expiry_date > issue_date", name="ck_licenses_dates"),
        Index("ix_licenses_facility_status", "facility_id", "status"),
        Index("ix_licenses_expiry_date", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    license_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    type: Mapped[LicenseType] = mapped_column(
        enum_type(LicenseType, "ck_licenses_type", 32), nullable=False
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[LicenseStatus] = mapped_column(
        enum_type(LicenseStatus, "ck_licenses_status", 20),
        nullable=False,
        default=LicenseStatus.ACTIVE,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    facility: Mapped[Facility] = relationship(back_populates="licenses")

    @property
    def is_expired(self) -> bool:
        """FR-12: flag licenses whose expiry date has passed."""

        return self.expiry_date < utc_today()
