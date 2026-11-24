"""Unit tests for password hashing."""

from app.auth.password import (
    hash_password,
    password_needs_rehash,
    verify_against_dummy,
    verify_password,
)


def test_hash_is_argon2id_and_salted(password_hash: str) -> None:
    another = hash_password("TestPassword_123!")
    assert password_hash.startswith("$argon2id$")
    assert another.startswith("$argon2id$")
    assert password_hash != another


def test_verify_password_accepts_correct_and_rejects_wrong(password_hash: str) -> None:
    assert verify_password("TestPassword_123!", password_hash) is True
    assert verify_password("WrongPassword_123!", password_hash) is False


def test_verify_password_handles_invalid_hash() -> None:
    assert verify_password("anything", "not-a-hash") is False
    assert password_needs_rehash("not-a-hash") is True


def test_new_hash_does_not_need_rehash(password_hash: str) -> None:
    assert password_needs_rehash(password_hash) is False


def test_dummy_verification_is_safe() -> None:
    assert verify_against_dummy("any-value") is None
