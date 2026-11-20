"""HTTP middleware: request correlation, access logs and security headers."""

from __future__ import annotations

import logging
import re
import secrets
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import Settings

logger = logging.getLogger(__name__)

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_DOCS_PATHS = {"/docs", "/redoc", "/docs/oauth2-redirect"}

_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
_WEB_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)
_DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def _client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_RE.fullmatch(incoming) else secrets.token_hex(8)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Return a generic 500 from inside the security-headers middleware
            # so error responses still carry hardening headers and a request ID.
            logger.exception(
                "Unhandled exception request_id=%s %s %s",
                request_id,
                request.method,
                request.url.path,
            )
            response = JSONResponse(status_code=500, content={"detail": "Internal server error."})
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        settings: Settings = request.app.state.settings
        log = logger.debug if request.url.path == "/health" else logger.info
        log(
            "%s %s -> %s in %.1fms client=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            _client_ip(request, settings),
            request_id,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        headers["Cross-Origin-Resource-Policy"] = "same-origin"
        headers["X-Permitted-Cross-Domain-Policies"] = "none"
        headers["Cache-Control"] = "no-store"
        path = request.url.path
        if path == "/" or path.startswith("/assets/"):
            csp = _WEB_CSP
        elif path in _DOCS_PATHS:
            csp = _DOCS_CSP
        else:
            csp = _API_CSP
        headers["Content-Security-Policy"] = csp
        forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
        if self.settings.enable_hsts and (
            request.url.scheme == "https" or forwarded_proto == "https"
        ):
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Do not advertise the server stack.
        if "server" in headers:
            del headers["server"]
        if "x-powered-by" in headers:
            del headers["x-powered-by"]
        return response
