"""Text helpers used when building SQL ``LIKE`` patterns.

The values themselves are always bound as SQL parameters by SQLAlchemy. This
helper only makes user-supplied ``%`` and ``_`` characters literal so a search
term cannot deliberately turn into a wildcard scan.
"""

from __future__ import annotations


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contains_pattern(value: str) -> str:
    """Return a safe ``%term%`` pattern for use with ``ilike(..., escape="\\")``."""

    return f"%{escape_like(value.strip())}%"
