class AmbienceGenerationError(Exception):
    pass


class AmbienceStorageError(Exception):
    pass


class LLMRateLimitError(Exception):
    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(f"LLM rate limited; retry after {retry_after}s")


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded; retry after {retry_after}s")
