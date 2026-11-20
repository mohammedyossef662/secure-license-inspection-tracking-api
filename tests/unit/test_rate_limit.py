"""Unit tests for the login rate limiter."""

from app.core.rate_limit import LoginRateLimiter


def test_blocks_after_threshold_and_counts_down(monkeypatch) -> None:
    now = [1000.0]
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: now[0])
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, ip_multiplier=2)
    scopes = limiter.scopes("203.0.113.10", "Inspector_A")

    assert limiter.retry_after(scopes) == 0
    for _ in range(3):
        limiter.record_failure(scopes)
    assert limiter.retry_after(scopes) == 60

    now[0] += 25
    assert limiter.retry_after(scopes) == 35

    now[0] += 36
    assert limiter.retry_after(scopes) == 0


def test_successful_login_resets_account_scope(monkeypatch) -> None:
    now = [2000.0]
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: now[0])
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60)
    scopes = limiter.scopes("203.0.113.11", "viewer_test")

    limiter.record_failure(scopes)
    limiter.record_failure(scopes)
    assert limiter.retry_after(scopes) > 0

    limiter.reset([scopes[0]])
    assert limiter.retry_after(scopes) == 0


def test_per_ip_limit_stops_username_spraying(monkeypatch) -> None:
    now = [3000.0]
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: now[0])
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60, ip_multiplier=2)

    for index in range(4):
        limiter.record_failure(limiter.scopes("203.0.113.12", f"user{index}"))

    # A brand-new username is still blocked from the same IP (limit 2 * 2).
    assert limiter.retry_after(limiter.scopes("203.0.113.12", "fresh_user")) > 0
    assert limiter.retry_after(limiter.scopes("203.0.113.13", "fresh_user")) == 0


def test_clear_removes_all_state(monkeypatch) -> None:
    now = [4000.0]
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: now[0])
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    scopes = limiter.scopes("203.0.113.14", "someone")
    limiter.record_failure(scopes)
    assert limiter.retry_after(scopes) > 0
    limiter.clear()
    assert limiter.retry_after(scopes) == 0
