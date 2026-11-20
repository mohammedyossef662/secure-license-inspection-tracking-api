"""Token hardening tests at the HTTP boundary.

These complement ``tests/unit/test_tokens.py`` by proving that the API rejects
malformed, expired, mis-scoped or forged tokens, and that the token's ``role``
claim can never be used to escalate privileges.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from app.core.config import Settings
from app.models import User


def _encode(settings: Settings, **overrides) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "username": "admin_test",
        "role": "admin",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": "security-test",
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_authenticates(client, settings, users) -> None:
    token = _encode(settings, sub=str(users["admin_test"].id), username="admin_test", role="admin")
    response = client.get("/users/me", headers=_bearer(token))
    assert response.status_code == 200
    assert response.json()["username"] == "admin_test"


def test_expired_token_is_rejected(client, settings, users) -> None:
    now = datetime.now(UTC)
    token = _encode(
        settings,
        sub=str(users["admin_test"].id),
        iat=now - timedelta(minutes=10),
        nbf=now - timedelta(minutes=10),
        exp=now - timedelta(minutes=5),
    )
    response = client.get("/users/me", headers=_bearer(token))
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials."
    assert response.headers["www-authenticate"] == "Bearer"


def test_not_yet_valid_token_is_rejected(client, settings, users) -> None:
    now = datetime.now(UTC)
    token = _encode(
        settings,
        sub=str(users["admin_test"].id),
        nbf=now + timedelta(minutes=5),
        iat=now + timedelta(minutes=5),
        exp=now + timedelta(minutes=10),
    )
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_tampered_signature_is_rejected(client, settings, users) -> None:
    token = _encode(settings, sub=str(users["admin_test"].id))
    header, payload, signature = token.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    tampered = f"{header}.{payload}.{signature[:-1]}{replacement}"
    assert client.get("/users/me", headers=_bearer(tampered)).status_code == 401


def test_token_signed_with_another_key_is_rejected(client, settings, users) -> None:
    token = jwt.encode(
        {
            "sub": str(users["admin_test"].id),
            "iat": datetime.now(UTC),
            "nbf": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        "attacker-controlled-signing-key-0123456789",
        algorithm="HS256",
    )
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_wrong_audience_is_rejected(client, settings, users) -> None:
    token = _encode(settings, sub=str(users["admin_test"].id), aud="some-other-api-clients")
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_wrong_issuer_is_rejected(client, settings, users) -> None:
    token = _encode(settings, sub=str(users["admin_test"].id), iss="another-issuer")
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_unsigned_alg_none_token_is_rejected(client, settings, users) -> None:
    token = jwt.encode(
        {
            "sub": str(users["admin_test"].id),
            "iat": datetime.now(UTC),
            "nbf": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        None,
        algorithm="none",
    )
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_missing_required_claim_is_rejected(client, settings, users) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(users["admin_test"].id),
            "iat": now,
            "nbf": now,
            # ``exp`` deliberately omitted; it is a required claim.
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.secret_key,
        algorithm="HS256",
    )
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_token_for_unknown_user_is_rejected(client, settings) -> None:
    token = _encode(settings, sub="999999", username="ghost", role="admin")
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_non_numeric_subject_is_rejected(client, settings) -> None:
    token = _encode(settings, sub="not-a-number")
    assert client.get("/users/me", headers=_bearer(token)).status_code == 401


def test_role_claim_cannot_elevate_a_viewer(client, settings, users) -> None:
    """Authorization reads the role from the database, not the token claim."""

    token = _encode(
        settings,
        sub=str(users["viewer_test"].id),
        username="viewer_test",
        role="admin",
    )
    headers = _bearer(token)

    me = client.get("/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "viewer"

    assert client.get("/users", headers=headers).status_code == 403
    assert client.get("/audit-logs", headers=headers).status_code == 403


def test_role_downgrade_takes_effect_without_reissue(client, settings, db, users) -> None:
    admin_id = users["admin_test"].id
    token = _encode(settings, sub=str(admin_id), username="admin_test", role="admin")
    headers = _bearer(token)

    assert client.get("/users", headers=headers).status_code == 200

    admin = db.get(User, admin_id)
    admin.role = "viewer"
    db.commit()

    assert client.get("/users", headers=headers).status_code == 403


def test_token_for_deactivated_user_is_rejected(client, settings, db, users) -> None:
    viewer_id = users["viewer_test"].id
    token = _encode(settings, sub=str(viewer_id), username="viewer_test", role="viewer")
    headers = _bearer(token)

    assert client.get("/users/me", headers=headers).status_code == 200

    viewer = db.get(User, viewer_id)
    viewer.is_active = False
    db.commit()

    assert client.get("/users/me", headers=headers).status_code == 401


def test_token_in_query_string_is_not_accepted(client, settings, users) -> None:
    token = _encode(settings, sub=str(users["admin_test"].id))
    for parameter in ("access_token", "token", "authorization"):
        response = client.get(f"/users/me?{parameter}={token}")
        assert response.status_code == 401, parameter


def test_bearer_scheme_is_required(client, settings, users) -> None:
    token = _encode(settings, sub=str(users["admin_test"].id))
    for value in (token, f"Basic {token}", "Bearer"):
        response = client.get("/users/me", headers={"Authorization": value})
        assert response.status_code == 401, value
