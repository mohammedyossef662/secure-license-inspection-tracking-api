"""Integration tests for health, root and OpenAPI endpoints."""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def test_health_check(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": "0.1.0"}


def test_health_returns_503_when_database_is_unavailable(client, monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise SQLAlchemyError("database is down")

    monkeypatch.setattr(Session, "execute", _boom)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert "database is down" not in response.text


def test_root_and_openapi(client) -> None:
    root = client.get("/api")
    assert root.status_code == 200
    assert root.json()["docs"] == "/docs"

    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    body = schema.json()
    assert body["info"]["title"] == "Regulatory License & Inspection Tracking API"
    for path in (
        "/auth/login",
        "/users",
        "/facilities",
        "/licenses",
        "/inspections",
        "/audit-logs",
    ):
        assert path in body["paths"]
    scheme = body["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert scheme["flows"]["password"]["tokenUrl"] == "/auth/login"


def test_docs_are_served(client) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_website_is_served_at_root(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Regulatory License" in response.text
    assert "openapi.json" in response.text

    asset = client.get("/assets/app.js")
    assert asset.status_code == 200
    assert "javascript" in asset.headers["content-type"]
