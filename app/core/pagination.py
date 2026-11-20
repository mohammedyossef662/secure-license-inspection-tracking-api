"""Pagination dependency and query helper."""

from __future__ import annotations

from math import ceil
from typing import Annotated, Any

from fastapi import Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


class Pagination:
    """Validated page/size query parameters."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="Items per page (max 100)")] = 20,
    ) -> None:
        self.page = page
        self.size = size
        self.offset = (page - 1) * size


PaginationDep = Annotated[Pagination, Depends()]


def paginate(db: Session, stmt: Select[Any], pagination: Pagination) -> dict[str, Any]:
    """Execute a paginated ``SELECT`` and return a serialisable page payload."""

    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    items = list(db.scalars(stmt.offset(pagination.offset).limit(pagination.size)).all())
    pages = ceil(total / pagination.size) if total else 0
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": pages,
    }
