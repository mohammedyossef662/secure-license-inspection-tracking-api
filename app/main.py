"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

from app.auth.revocation import TokenRevocation
from app.core.config import Settings, get_settings
from app.core.database import build_engine, build_session_factory
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import LoginRateLimiter
from app.routers import audit_logs, auth, facilities, health, inspections, licenses, users

OPENAPI_TAGS = [
    {"name": "Operations", "description": "Health and readiness endpoints."},
    {"name": "Authentication", "description": "Obtain and use JWT access tokens."},
    {"name": "Users", "description": "Account administration and self-service profile."},
    {"name": "Facilities", "description": "Regulated facilities."},
    {"name": "Licenses", "description": "Licenses issued to facilities."},
    {"name": "Inspections", "description": "Compliance inspections and findings."},
    {"name": "Audit logs", "description": "Traceability of security-relevant events (Admin only)."},
]

DESCRIPTION = """
A secure REST API for tracking regulated facilities, their licenses and
inspection records.

**Roles:** `admin` (full access), `inspector` (records and updates their own
inspections), `viewer` (read-only).

All data is fictional. See the repository `docs/` directory for requirements,
architecture, threat model, test plan and deployment guidance.
"""

# Static website (landing page) served at "/". API routes are registered before
# the mount, so they always take precedence over static files.
WEB_DIR = Path(__file__).resolve().parent.parent / "docs"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        engine.dispose()

    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        contact={
            "name": "Mohamed Yossef Mohamed",
            "url": "https://www.linkedin.com/in/mohamedyossef963",
        },
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.login_limiter = LoginRateLimiter(
        max_attempts=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
        ip_multiplier=settings.login_rate_limit_ip_multiplier,
    )
    app.state.token_revocation = TokenRevocation()

    register_exception_handlers(app)

    # Middleware is applied in reverse order of registration: TrustedHost is
    # outermost, then security headers, request context and CORS.
    if settings.allowed_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
            max_age=600,
        )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    if settings.allowed_hosts_list != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(facilities.router)
    app.include_router(licenses.router)
    app.include_router(inspections.router)
    app.include_router(audit_logs.router)

    @app.get("/api", include_in_schema=False)
    def api_info() -> dict[str, str | None]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": docs_url,
            "openapi": openapi_url,
        }

    if WEB_DIR.is_dir():
        index_file = WEB_DIR / "index.html"
        if index_file.is_file():

            @app.get("/", include_in_schema=False)
            def website() -> FileResponse:
                return FileResponse(index_file)

        assets_dir = WEB_DIR / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="website-assets")

    # Cap accepted request bodies (JSON) to mitigate large-payload abuse.
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=64 * 1024)

    return app


app = create_app()
