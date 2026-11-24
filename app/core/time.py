"""UTC helpers.

The application stores naive UTC datetimes because MySQL ``DATETIME`` does not
preserve time zones. All values leaving the API are therefore UTC.
"""

from __future__ import annotations

from datetime import UTC, date, datetime


def utcnow() -> datetime:
    """Return the current time as a naive UTC datetime."""

    return datetime.now(UTC).replace(tzinfo=None)


def utc_today() -> date:
    """Return the current UTC date."""

    return datetime.now(UTC).date()
