from typing import Protocol


class RateLimiter(Protocol):
    def check(self, user_id: str) -> None: ...
