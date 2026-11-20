"""In-memory JWT revocation (token denylist).

A signed access token that has been explicitly revoked (for example through
``POST /auth/logout``) is rejected until its original ``exp`` claim passes.
The store is intentionally process-local; deployments running more than one API
instance should replace it with a shared store such as Redis (see
``docs/02-architecture.md``).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime


class TokenRevocation:
    """Process-local token denylist keyed by ``jti`` with expiry."""

    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, expires_at: datetime) -> None:
        """Blacklist ``jti`` until the token's original expiry."""

        with self._lock:
            self._revoked[jti] = expires_at.timestamp()

    def is_revoked(self, jti: str) -> bool:
        """Return ``True`` when the token is still revoked."""

        now = time.monotonic()
        with self._lock:
            expires_at = self._revoked.get(jti)
            if expires_at is None:
                return False
            if expires_at <= now:
                self._revoked.pop(jti, None)
                return False
            return True

    def clear(self) -> None:
        with self._lock:
            self._revoked.clear()
