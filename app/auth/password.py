"""Password hashing with Argon2id."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# OWASP-recommended Argon2id parameters (19 MiB, 2 iterations, 1 lane) are
# exceeded by argon2-cffi's defaults, so the library defaults are kept.
_hasher = PasswordHasher()

# Used to equalise response time when a username does not exist, reducing the
# ability to enumerate accounts through timing differences.
_DUMMY_HASH = _hasher.hash("timing-equalisation-only-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def verify_against_dummy(password: str) -> None:
    """Spend the same hashing work as a real verification for unknown users."""

    verify_password(password, _DUMMY_HASH)
