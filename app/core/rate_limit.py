"""In-process login rate limiter.

A sliding-window limiter keyed by client IP and normalised username. It blocks
further attempts once the failure count reaches the configured threshold for
the window, and returns a ``Retry-After`` value based on the oldest failure.

This is deliberately dependency-free and per-process. For multi-worker or
multi-instance deployments, replace it with a shared Redis-backed limiter; see
``docs/02-architecture.md``.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Sequence


class LoginRateLimiter:
    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        ip_multiplier: int = 5,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.ip_limit = max_attempts * ip_multiplier
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._operations = 0

    def scopes(self, ip: str, username: str) -> list[tuple[str, int]]:
        normalised = username.strip().lower()
        return [
            (f"account:{ip}:{normalised}", self.max_attempts),
            (f"ip:{ip}", self.ip_limit),
        ]

    def _prune(self, events: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while events and events[0] <= cutoff:
            events.popleft()

    def retry_after(self, scopes: Sequence[tuple[str, int]]) -> int:
        """Return seconds to wait, or 0 when the attempt is allowed."""

        now = time.monotonic()
        retry = 0
        with self._lock:
            for key, limit in scopes:
                events = self._events.get(key)
                if not events:
                    continue
                self._prune(events, now)
                if not events:
                    self._events.pop(key, None)
                    continue
                if len(events) >= limit:
                    retry = max(retry, math.ceil(events[0] + self.window_seconds - now))
        return max(retry, 0)

    def record_failure(self, scopes: Sequence[tuple[str, int]]) -> None:
        now = time.monotonic()
        with self._lock:
            for key, limit in scopes:
                events = self._events.get(key)
                if events is None:
                    events = deque(maxlen=limit)
                    self._events[key] = events
                self._prune(events, now)
                events.append(now)
            self._operations += 1
            if self._operations % 256 == 0:
                self._cleanup(now)

    def reset(self, scopes: Sequence[tuple[str, int]]) -> None:
        with self._lock:
            for key, _ in scopes:
                self._events.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def _cleanup(self, now: float) -> None:
        cutoff = now - self.window_seconds
        stale = [key for key, events in self._events.items() if not events or events[-1] <= cutoff]
        for key in stale:
            self._events.pop(key, None)
