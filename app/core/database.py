"""Database engine and session management.

The engine/session factory live on ``app.state`` so tests can build an isolated
application instance without touching process-wide globals.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Any

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine appropriate for the configured database."""

    options: dict[str, Any] = {
        "pool_pre_ping": True,
        "echo": settings.database_echo,
    }
    if settings.database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in settings.database_url:
            options["poolclass"] = StaticPool
    else:
        options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_recycle=settings.database_pool_recycle,
        )
    return create_engine(settings.database_url, **options)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped session and guarantee rollback on failure."""

    factory: sessionmaker[Session] = request.app.state.session_factory
    db = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
