"""Unit tests for configuration guards."""

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_allowed_origins_and_hosts_are_parsed() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        secret_key="a" * 40,
        environment="test",
        allowed_origins="http://localhost:3000, https://example.org ",
        allowed_hosts="api.example.org, localhost",
    )
    assert settings.allowed_origins_list == ["http://localhost:3000", "https://example.org"]
    assert settings.allowed_hosts_list == ["api.example.org", "localhost"]
    assert settings.is_production is False


def test_short_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            secret_key="short",
            environment="test",
        )


def test_production_requires_mysql_and_hardened_settings() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            secret_key="a" * 40,
            environment="production",
            allowed_hosts="api.example.org",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="mysql+pymysql://user:pass@db/app",
            secret_key="change-me-" + "a" * 40,
            environment="production",
            allowed_hosts="api.example.org",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="mysql+pymysql://user:pass@db/app",
            secret_key="a" * 40,
            environment="production",
            allowed_hosts="*",
        )


def test_production_accepts_hardened_settings() -> None:
    settings = Settings(
        _env_file=None,
        database_url="mysql+pymysql://user:pass@db/app",
        secret_key="a" * 40,
        environment="production",
        allowed_hosts="api.example.org",
    )
    assert settings.is_production is True
