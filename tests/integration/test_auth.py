"""Integration tests for authentication and token handling."""

from __future__ import annotations

from app.core.rate_limit import LoginRateLimiter
from app.models import AuditLog, User
from sqlalchemy import select

from tests.conftest import TEST_PASSWORD
from tests.factories import create_user


def test_login_json_returns_token_and_user(client, users) -> None:
    response = client.post(
        "/auth/login", json={"username": "admin_test", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["access_token"].count(".") == 2
    assert body["user"]["username"] == "admin_test"
    assert body["user"]["role"] == "admin"
    assert body["user"]["last_login_at"] is not None
    assert "password" not in body["user"]


def test_login_accepts_oauth2_form_body(client, users) -> None:
    response = client.post(
        "/auth/login",
        data={"username": "viewer_test", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "viewer"


def test_login_normalises_username(client, users) -> None:
    response = client.post(
        "/auth/login", json={"username": "  ADMIN_TEST  ", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "admin_test"


def test_wrong_password_and_unknown_user_return_identical_generic_errors(client, users) -> None:
    wrong = client.post(
        "/auth/login", json={"username": "admin_test", "password": "WrongPassword_123!"}
    )
    unknown = client.post(
        "/auth/login", json={"username": "does_not_exist", "password": "WrongPassword_123!"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["detail"] == "Invalid username or password."
    assert wrong.headers["www-authenticate"] == "Bearer"


def test_inactive_account_cannot_log_in(client, db, password_hash) -> None:
    create_user(db, "inactive_user", "viewer", password_hash, is_active=False)
    response = client.post(
        "/auth/login", json={"username": "inactive_user", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_missing_or_malformed_token_is_rejected(client) -> None:
    missing = client.get("/facilities")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert client.get("/facilities", headers={"Authorization": "Bearer"}).status_code == 401
    assert client.get("/facilities", headers={"Authorization": "Token abc"}).status_code == 401
    assert (
        client.get("/facilities", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401
    )


def test_deactivated_user_token_is_rejected(client, db, auth, users) -> None:
    headers = auth["viewer_test"]
    assert client.get("/users/me", headers=headers).status_code == 200
    user = db.get(User, users["viewer_test"].id)
    user.is_active = False
    db.commit()
    assert client.get("/users/me", headers=headers).status_code == 401


def test_login_validation_does_not_echo_secrets(client, users) -> None:
    long_password = "P" * 200
    response = client.post(
        "/auth/login", json={"username": "admin_test", "password": long_password}
    )
    assert response.status_code == 422
    assert long_password not in response.text
    assert "input" not in response.text


def test_login_rejects_malformed_bodies(client) -> None:
    assert (
        client.post(
            "/auth/login",
            content="this is not json",
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert client.post("/auth/login", json=[]).status_code == 422
    assert client.post("/auth/login", json={}).status_code == 422
    assert client.post("/auth/login", json={"username": "admin_test"}).status_code == 422


def test_login_rate_limit_returns_429_and_retry_after(client, app, users) -> None:
    app.state.login_limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, ip_multiplier=5)
    for _ in range(3):
        response = client.post(
            "/auth/login", json={"username": "admin_test", "password": "WrongPassword_123!"}
        )
        assert response.status_code == 401

    blocked = client.post("/auth/login", json={"username": "admin_test", "password": TEST_PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert blocked.json()["detail"] == "Too many login attempts. Try again later."

    app.state.login_limiter.clear()
    recovered = client.post(
        "/auth/login", json={"username": "admin_test", "password": TEST_PASSWORD}
    )
    assert recovered.status_code == 200


def test_audit_log_records_login_success_and_failure(client, db, users) -> None:
    client.post("/auth/login", json={"username": "admin_test", "password": TEST_PASSWORD})
    client.post("/auth/login", json={"username": "admin_test", "password": "WrongPassword_123!"})
    actions = list(db.scalars(select(AuditLog.action).order_by(AuditLog.id)).all())
    assert "login_success" in actions
    assert "login_failed" in actions
    success = db.scalar(select(AuditLog).where(AuditLog.action == "login_success"))
    assert success is not None
    assert success.user_id == users["admin_test"].id
    assert success.timestamp is not None
    failed = db.scalar(select(AuditLog).where(AuditLog.action == "login_failed"))
    assert failed is not None
    assert failed.details == "reason=invalid_credentials"


def test_logout_revokes_the_access_token(client, users) -> None:
    token_response = client.post(
        "/auth/login", json={"username": "admin_test", "password": TEST_PASSWORD}
    )
    token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/users/me", headers=headers).status_code == 200

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/users/me", headers=headers).status_code == 401
    assert client.post("/auth/logout", headers=headers).status_code == 401
