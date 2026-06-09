import pytest

from app.models.errors import RateLimitExceeded
from app.ratelimit.in_memory import InMemoryRateLimiter


def test_allows_requests_under_limit() -> None:
    limiter = InMemoryRateLimiter(limit=3, window_seconds=60)
    limiter.check("u1")
    limiter.check("u1")
    limiter.check("u1")  # 3rd — still allowed


def test_blocks_on_limit_exceeded() -> None:
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    limiter.check("u1")
    limiter.check("u1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("u1")


def test_rate_limit_exceeded_carries_retry_after() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=30)
    limiter.check("u1")
    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter.check("u1")
    assert exc_info.value.retry_after == 30


def test_different_users_are_independent() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    limiter.check("u1")
    limiter.check("u2")  # different user — should not raise


def test_expired_calls_do_not_count() -> None:
    import time
    limiter = InMemoryRateLimiter(limit=1, window_seconds=1)
    limiter.check("u1")
    time.sleep(1.1)
    limiter.check("u1")  # old call expired — should not raise
