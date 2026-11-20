"""Application configuration.

All secrets and environment-specific values are supplied through environment
variables (or a local ``.env`` file). Nothing sensitive is hard-coded here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Regulatory License & Inspection Tracking API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    docs_enabled: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_recycle: int = Field(default=1800, ge=60)

    # Authentication / JWT
    secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "license-inspection-api"
    jwt_audience: str = "license-inspection-api-clients"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)

    # HTTP security
    allowed_origins: str = ""
    allowed_hosts: str = "*"
    trust_proxy_headers: bool = False
    enable_hsts: bool = False

    # Login rate limiting (per-process; see docs/02-architecture.md)
    login_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    login_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    login_rate_limit_ip_multiplier: int = Field(default=5, ge=1, le=100)

    # Development helpers
    seed_on_start: bool = False

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        value = value.strip().upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if value not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if not self.is_production:
            return self
        if not self.database_url.startswith("mysql"):
            raise ValueError("production requires a MySQL DATABASE_URL")
        if "change-me" in self.secret_key.lower() or "changeme" in self.secret_key.lower():
            raise ValueError("SECRET_KEY must not contain a placeholder value in production")
        if self.allowed_hosts_list == ["*"]:
            raise ValueError("ALLOWED_HOSTS must be restricted in production")
        return self

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        hosts = [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
        return hosts or ["*"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (cached)."""

    return Settings()  # type: ignore[call-arg]  # values come from the environment
