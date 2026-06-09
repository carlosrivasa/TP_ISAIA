from __future__ import annotations

import time
from collections import defaultdict

from app.models.errors import RateLimitExceeded


class InMemoryRateLimiter:
    """Fixed-window rate limiter keyed by user_id.

    Not suitable for multi-process or multi-instance deployments — use a
    Redis-backed implementation in production.
    """

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._log: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> None:
        now = time.monotonic()
        cutoff = now - self._window
        calls = [t for t in self._log[user_id] if t > cutoff]
        if len(calls) >= self._limit:
            raise RateLimitExceeded(retry_after=self._window)
        calls.append(now)
        self._log[user_id] = calls
