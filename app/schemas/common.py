"""Shared schema building blocks and reusable validated field types."""

from __future__ import annotations

import re
from typing import Annotated, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

T = TypeVar("T")

_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,49}$")
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-/]{2,49}$")
_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,128}$")


class StrictModel(BaseModel):
    """Request model that rejects unknown fields (prevents mass assignment)."""

    model_config = ConfigDict(extra="forbid")


class ORMModel(BaseModel):
    """Response model populated from ORM attributes."""

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


def _normalise_username(value: str) -> str:
    value = value.strip().lower()
    if not _USERNAME_RE.fullmatch(value):
        raise ValueError(
            "username must be 3-50 characters, start with a letter or digit, and contain only "
            "letters, digits, '.', '_' or '-'"
        )
    return value


def _normalise_code(value: str) -> str:
    value = value.strip().upper()
    if not _CODE_RE.fullmatch(value):
        raise ValueError(
            "value must be 3-50 characters, start with a letter or digit, and contain only "
            "letters, digits, '-' or '/'"
        )
    return value


def _validate_password(value: str) -> str:
    if not _PASSWORD_RE.fullmatch(value):
        raise ValueError(
            "password must be at least 12 characters and contain upper, lower, digit and "
            "special characters"
        )
    return value


Username = Annotated[str, Field(min_length=3, max_length=50), AfterValidator(_normalise_username)]
LoginUsername = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=50)
]
Code = Annotated[str, Field(min_length=3, max_length=50), AfterValidator(_normalise_code)]
Password = Annotated[str, Field(min_length=12, max_length=128), AfterValidator(_validate_password)]
LoginPassword = Annotated[str, Field(min_length=1, max_length=128)]
FullName = Annotated[str, StringConstraints(min_length=2, max_length=120)]
FacilityName = Annotated[str, StringConstraints(min_length=2, max_length=200)]
Address = Annotated[str, StringConstraints(min_length=5, max_length=500)]
Notes = Annotated[str, StringConstraints(max_length=2000)]
