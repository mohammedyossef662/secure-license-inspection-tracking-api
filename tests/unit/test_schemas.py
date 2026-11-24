"""Unit tests for schema validation and normalisation."""

from datetime import date, timedelta

import pytest
from app.core.text import contains_pattern, escape_like
from app.schemas.facility import FacilityCreate
from app.schemas.inspection import InspectionCreate
from app.schemas.license import LicenseCreate
from app.schemas.user import ProfileUpdate, UserAdminUpdate, UserCreate
from pydantic import ValidationError


def test_username_is_trimmed_and_lowercased() -> None:
    user = UserCreate(username="  Admin.User  ", password="Str0ng!Passw0rd")
    assert user.username == "admin.user"


@pytest.mark.parametrize("username", ["ab", "bad name", "üser", "x" * 51, "---"])
def test_invalid_usernames_are_rejected(username: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(username=username, password="Str0ng!Passw0rd")


def test_short_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="valid_name", password="A" * 11)


@pytest.mark.parametrize(
    "password",
    [
        "passwordonlyupper123",  # no upper case, no special character
        "PASSWORDUPPER12345",  # no lower case, no special character
        "PasswordOnlyUpper123",  # no digit, no special character
        "PasswordOnlyUpper1234",  # no digit, no special character
        "Str0ng!Pass",  # too short
    ],
)
def test_weak_passwords_are_rejected(password: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="valid_name", password=password)


def test_strong_password_is_accepted() -> None:
    user = UserCreate(username="valid_name", password="Str0ng!Passw0rd")
    assert user.password == "Str0ng!Passw0rd"


def test_codes_are_trimmed_and_uppercased() -> None:
    facility = FacilityCreate(
        name="Acme",
        registration_number=" reg-100 ",
        address="12 Industrial Road",
    )
    assert facility.registration_number == "REG-100"


def test_invalid_code_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FacilityCreate(name="Acme", registration_number="-bad", address="12 Industrial Road")


def test_unknown_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        FacilityCreate(
            name="Acme",
            registration_number="REG-1",
            address="12 Industrial Road",
            is_deleted=True,
        )


def test_license_expiry_must_follow_issue_date() -> None:
    today = date.today()
    with pytest.raises(ValidationError):
        LicenseCreate(
            facility_id=1,
            license_number="LIC-1",
            type="operating",
            issue_date=today,
            expiry_date=today,
        )


def test_inspection_date_cannot_be_in_the_future() -> None:
    with pytest.raises(ValidationError):
        InspectionCreate(
            facility_id=1,
            inspection_date=date.today() + timedelta(days=1),
            result="compliant",
        )


def test_empty_update_payloads_are_rejected() -> None:
    with pytest.raises(ValidationError):
        UserAdminUpdate()
    with pytest.raises(ValidationError):
        ProfileUpdate()


def test_password_change_requires_current_password() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate(new_password="AnotherPassword_123!")


def test_like_patterns_escape_wildcards() -> None:
    assert escape_like("100%_done\\") == "100\\%\\_done\\\\"
    assert contains_pattern("  acme  ") == "%acme%"
