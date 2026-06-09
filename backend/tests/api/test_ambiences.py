from fastapi.testclient import TestClient

from app.models.ambience import Ambience, AmbienceRequest
from app.models.errors import (
    AmbienceGenerationError,
    AmbienceStorageError,
    LLMRateLimitError,
    RateLimitExceeded,
)


class _FakeService:
    def __init__(self, result: Ambience) -> None:
        self._result = result

    def create(self, request: AmbienceRequest) -> Ambience:
        return self._result


class _RaisingService:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def create(self, request: AmbienceRequest) -> Ambience:
        raise self._exc


class _PassLimiter:
    def check(self, user_id: str) -> None:
        pass


class _BlockLimiter:
    def check(self, user_id: str) -> None:
        raise RateLimitExceeded(retry_after=30)


def _make_client(service: object, limiter: object) -> TestClient:
    from app.main import create_app

    app = create_app(service=service, rate_limiter=limiter)
    return TestClient(app, raise_server_exceptions=False)


def test_create_returns_201(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 201


def test_create_returns_location_header(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.headers["location"] == f"/ambiences/{sample_ambience.uuid}"


def test_create_response_contains_uuid(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.json()["uuid"] == sample_ambience.uuid


def test_create_response_contains_fingerprint(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.json()["fingerprint"] == sample_ambience.fingerprint


def test_missing_prompt_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"user_id": "u1"})
    assert res.status_code == 422


def test_missing_user_id_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz"})
    assert res.status_code == 422


def test_prompt_too_short_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "ab", "user_id": "u1"})
    assert res.status_code == 422


def test_prompt_too_long_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "x" * 2001, "user_id": "u1"})
    assert res.status_code == 422


def test_rate_limit_returns_429(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _BlockLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 429


def test_rate_limit_includes_retry_after_header(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _BlockLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.headers.get("retry-after") == "30"


def test_generation_error_returns_502(sample_ambience: Ambience) -> None:
    svc = _RaisingService(AmbienceGenerationError("fail"))
    client = _make_client(svc, _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 502


def test_llm_rate_limit_returns_503(sample_ambience: Ambience) -> None:
    svc = _RaisingService(LLMRateLimitError(retry_after=60))
    client = _make_client(svc, _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 503


def test_llm_rate_limit_includes_retry_after(sample_ambience: Ambience) -> None:
    svc = _RaisingService(LLMRateLimitError(retry_after=60))
    client = _make_client(svc, _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.headers.get("retry-after") == "60"


def test_storage_error_returns_503(sample_ambience: Ambience) -> None:
    client = _make_client(_RaisingService(AmbienceStorageError("full")), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 503


def test_error_response_does_not_leak_internals(sample_ambience: Ambience) -> None:
    client = _make_client(
        _RaisingService(AmbienceGenerationError("secret trace")), _PassLimiter()
    )
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert "secret trace" not in res.text
