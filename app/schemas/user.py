"""User schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from app.models.enums import UserRole
from app.schemas.common import FullName, LoginPassword, ORMModel, Password, StrictModel, Username


class UserCreate(StrictModel):
    username: Username
    password: Password
    full_name: FullName | None = None
    role: UserRole = UserRole.VIEWER


class UserAdminUpdate(StrictModel):
    full_name: FullName | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: Password | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> UserAdminUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ProfileUpdate(StrictModel):
    full_name: FullName | None = None
    current_password: LoginPassword | None = None
    new_password: Password | None = None

    @model_validator(mode="after")
    def _validate_password_change(self) -> ProfileUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if self.new_password is not None and self.current_password is None:
            raise ValueError("current_password is required when changing the password")
        return self


class UserRead(ORMModel):
    id: int
    username: str
    full_name: str | None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
