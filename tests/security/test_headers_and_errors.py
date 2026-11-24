"""Security header, CORS, host validation and error-handling tests."""

from __future__ import annotations

import re

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _new_client(
    settings: Settings,
    *,
    base_url: str = "http://testserver",
    **overrides: object,
) -> tuple[object, TestClient]:
    configured = settings.model_copy(update=overrides)
    application = create_app(configured)
    return application, TestClient(application, base_url=base_url, raise_server_exceptions=False)


def test_hardening_headers_are_present_on_success(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == ("geolocation=(), microphone=(), camera=()")
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["x-permitted-cross-domain-policies"] == "none"
    assert response.headers["cache-control"] == "no-store"
    assert "server" not in response.headers
    assert "x-powered-by" not in response.headers


def test_api_csp_is_restrictive_and_docs_csp_allows_swagger(client) -> None:
    api = client.get("/api")
    csp = api.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "cdn.jsdelivr.net" not in csp

    website = client.get("/")
    assert website.status_code == 200
    web_csp = website.headers["content-security-policy"]
    assert "default-src 'self'" in web_csp
    assert "script-src 'self'" in web_csp
    assert "cdn.jsdelivr.net" not in web_csp

    docs = client.get("/docs")
    assert docs.status_code == 200
    docs_csp = docs.headers["content-security-policy"]
    assert "default-src 'self'" in docs_csp
    assert "cdn.jsdelivr.net" in docs_csp
    assert "frame-ancestors 'none'" in docs_csp


def test_hardening_headers_are_present_on_error_responses(client) -> None:
    for response in (
        client.get("/does-not-exist"),
        client.get("/users/me"),
        client.post("/health"),
    ):
        assert response.status_code in {401, 404, 405}
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["content-security-policy"]


def test_request_id_is_echoed_when_valid(client) -> None:
    response = client.get("/", headers={"X-Request-ID": "trace-abc_123.4"})
    assert response.headers["x-request-id"] == "trace-abc_123.4"


def test_request_id_is_generated_when_missing_or_invalid(client) -> None:
    for headers in ({}, {"X-Request-ID": "contains spaces and <html>"}, {"X-Request-ID": ""}):
        response = client.get("/", headers=headers)
        generated = response.headers["x-request-id"]
        assert generated
        assert _REQUEST_ID_RE.fullmatch(generated)
        assert " " not in generated
        assert "<" not in generated
        assert len(generated) == 16


def test_hsts_only_on_https_when_enabled(settings: Settings) -> None:
    _, https_client = _new_client(settings, base_url="https://testserver", enable_hsts=True)
    try:
        assert "strict-transport-security" in https_client.get("/").headers
    finally:
        https_client.close()

    _, http_client = _new_client(settings, base_url="http://testserver", enable_hsts=True)
    try:
        assert "strict-transport-security" not in http_client.get("/").headers
        forwarded = http_client.get("/", headers={"X-Forwarded-Proto": "https"})
        assert "strict-transport-security" in forwarded.headers
    finally:
        http_client.close()

    _, disabled_client = _new_client(settings, base_url="https://testserver", enable_hsts=False)
    try:
        assert "strict-transport-security" not in disabled_client.get("/").headers
    finally:
        disabled_client.close()


def test_trusted_host_middleware_rejects_unknown_hosts(settings: Settings) -> None:
    _, rejected = _new_client(settings, allowed_hosts="api.example.org")
    try:
        assert rejected.get("/").status_code == 400
    finally:
        rejected.close()

    _, accepted = _new_client(
        settings, base_url="http://api.example.org", allowed_hosts="api.example.org"
    )
    try:
        assert accepted.get("/").status_code == 200
    finally:
        accepted.close()


def test_cors_preflight_allows_only_configured_origins(settings: Settings) -> None:
    _, client = _new_client(settings, allowed_origins="https://app.example.org")
    try:
        preflight = client.options(
            "/health",
            headers={
                "Origin": "https://app.example.org",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == ("https://app.example.org")
        assert "authorization" in preflight.headers["access-control-allow-headers"].lower()

        blocked = client.options(
            "/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in blocked.headers

        simple = client.get("/", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in simple.headers
    finally:
        client.close()


def test_unhandled_errors_are_generic_and_still_hardened(client, app) -> None:
    @app.get("/_boom", include_in_schema=False)
    def _boom() -> None:
        raise RuntimeError("internal-detail-that-must-not-leak")

    response = client.get("/_boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}
    assert "internal-detail-that-must-not-leak" not in response.text
    assert "traceback" not in response.text.lower()
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_docs_can_be_disabled(settings: Settings) -> None:
    application, client = _new_client(settings, docs_enabled=False)
    try:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        root = client.get("/api")
        assert root.status_code == 200
        assert root.json()["docs"] is None
        assert root.json()["openapi"] is None
        assert application.openapi_url is None
    finally:
        client.close()


def test_unknown_routes_and_methods_return_clean_errors(client) -> None:
    missing = client.get("/this-route-does-not-exist")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Not Found"}

    wrong_method = client.post("/health")
    assert wrong_method.status_code == 405
    assert "allow" in wrong_method.headers
    assert "GET" in wrong_method.headers["allow"]

    unsupported = client.request("TRACE", "/health")
    assert unsupported.status_code == 405


def test_validation_errors_never_echo_submitted_values(client) -> None:
    secret = "SuperSecretPassword_123!"
    response = client.post(
        "/auth/login", json={"username": "x", "password": secret, "extra": secret}
    )
    assert response.status_code == 422
    assert secret not in response.text
    assert '"input"' not in response.text
    assert '"ctx"' not in response.text
    errors = response.json()["detail"]
    assert isinstance(errors, list)
    for error in errors:
        assert set(error).issubset({"loc", "msg", "type"})


def test_oversized_request_body_is_rejected(client) -> None:
    big_payload = {"username": "u" * 40000, "password": "p" * 40000}
    response = client.post("/auth/login", json=big_payload)
    assert response.status_code == 413
