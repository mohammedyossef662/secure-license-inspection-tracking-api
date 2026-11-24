"""Shared pytest fixtures.

Tests run against a per-test SQLite database locally. CI sets
``TEST_DATABASE_URL`` to MySQL 8, so the same suite exercises the production
database engine there.
"""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-0123456789-abcdefghijklmnop")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from collections.abc import Iterator
from pathlib import Path

import pytest
from app.auth.password import hash_password
from app.core.config import Settings
from app.main import create_app
from app.models import Base
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from tests.factories import create_user

TEST_PASSWORD = "TestPassword_123!"
TEST_SECRET_KEY = "test-only-secret-key-0123456789-abcdefghijklmnop"


@event.listens_for(Engine, "connect")
def _enable_sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
    if "sqlite3" in type(dbapi_connection).__module__:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        database_url = f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}"
    return Settings(
        _env_file=None,
        database_url=database_url,
        secret_key=TEST_SECRET_KEY,
        environment="test",
        docs_enabled=True,
        allowed_origins="",
        allowed_hosts="*",
        login_rate_limit_attempts=5,
        login_rate_limit_window_seconds=60,
        access_token_expire_minutes=15,
    )


@pytest.fixture
def app(settings: Settings):
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)
    yield application
    Base.metadata.drop_all(application.state.engine)
    application.state.engine.dispose()


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def db(app) -> Iterator[Session]:
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def password_hash() -> str:
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def users(db: Session, password_hash: str):
    return {
        "admin_test": create_user(db, "admin_test", "admin", password_hash, "Admin Test"),
        "inspector_a": create_user(db, "inspector_a", "inspector", password_hash, "Inspector A"),
        "inspector_b": create_user(db, "inspector_b", "inspector", password_hash, "Inspector B"),
        "viewer_test": create_user(db, "viewer_test", "viewer", password_hash, "Viewer Test"),
    }


@pytest.fixture
def login(client: TestClient):
    def _login(username: str, password: str = TEST_PASSWORD) -> dict[str, str]:
        response = client.post("/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def auth(users, login):
    return {username: login(username) for username in users}
