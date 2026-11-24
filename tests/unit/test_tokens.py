"""Unit tests for JWT creation and verification."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.auth.tokens import create_access_token, decode_access_token
from app.core.config import Settings
from app.models import User, UserRole


def _user() -> User:
    return User(
        id=7,
        username="inspector_a",
        password_hash="unused",
        role=UserRole.INSPECTOR,
        is_active=True,
    )


def _payload(settings: Settings, **overrides) -> dict:
    now = datetime.now(UTC)
    payload = {
        "sub": "7",
        "username": "inspector_a",
        "role": "inspector",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    payload.update(overrides)
    return payload


def test_create_and_decode_token(settings: Settings) -> None:
    token, expires_in = create_access_token(_user(), settings)
    assert expires_in == 900
    payload = decode_access_token(token, settings)
    assert payload["sub"] == "7"
    assert payload["username"] == "inspector_a"
    assert payload["role"] == "inspector"
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience


def test_expired_token_is_rejected(settings: Settings) -> None:
    token = jwt.encode(
        _payload(settings, exp=datetime.now(UTC) - timedelta(seconds=1)),
        settings.secret_key,
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, settings)


def test_tampered_token_is_rejected(settings: Settings) -> None:
    token, _ = create_access_token(_user(), settings)
    header, payload, signature = token.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    tampered = f"{header}.{payload}.{signature[:-1]}{replacement}"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered, settings)


def test_token_signed_with_another_key_is_rejected(settings: Settings) -> None:
    token, _ = create_access_token(_user(), settings)
    other = Settings(
        _env_file=None,
        database_url=settings.database_url,
        secret_key="a-completely-different-secret-key-0123456789",
        environment="test",
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, other)


def test_wrong_issuer_or_audience_is_rejected(settings: Settings) -> None:
    token, _ = create_access_token(_user(), settings)
    other = Settings(
        _env_file=None,
        database_url=settings.database_url,
        secret_key=settings.secret_key,
        environment="test",
        jwt_issuer="someone-else",
        jwt_audience="someone-else",
    )
    with pytest.raises(jwt.InvalidIssuerError):
        decode_access_token(token, other)


def test_missing_required_claim_is_rejected(settings: Settings) -> None:
    payload = _payload(settings)
    payload.pop("exp")
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token, settings)


def test_alg_none_token_is_rejected(settings: Settings) -> None:
    token = jwt.encode(_payload(settings), None, algorithm="none")
    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(token, settings)
