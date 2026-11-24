"""Unauthenticated health check for containers and load balancers."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.auth.dependencies import DbDep

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Operations"])


@router.get("/health", summary="Liveness/readiness check")
def health(request: Request, db: DbDep) -> JSONResponse:
    version = request.app.state.settings.app_version
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Health check failed: database unavailable")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable", "version": version},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "database": "ok", "version": version},
    )
