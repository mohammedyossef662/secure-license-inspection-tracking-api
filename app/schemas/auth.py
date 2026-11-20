"""Authentication request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import LoginPassword, LoginUsername, StrictModel
from app.schemas.user import UserRead


class LoginRequest(StrictModel):
    username: LoginUsername
    password: LoginPassword


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - fixed token type, not a secret
    expires_in: int
    user: UserRead
