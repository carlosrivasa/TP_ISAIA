import pytest

from app.models.ambience import Ambience, AmbienceContent, AmbienceRequest, Filter
from app.models.errors import AmbienceGenerationError, AmbienceStorageError
from app.services.ambience_service import AmbienceService


class _FakePipeline:
    def __init__(self, content: AmbienceContent) -> None:
        self._content = content

    def run(self, prompt: str) -> AmbienceContent:
        return self._content


class _RaisingPipeline:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def run(self, prompt: str) -> AmbienceContent:
        raise self._exc


class _FakeStore:
    def __init__(self) -> None:
        self.saved: list[Ambience] = []

    def save(self, ambience: Ambience) -> None:
        self.saved.append(ambience)


class _FailingStore:
    def save(self, ambience: Ambience) -> None:
        raise AmbienceStorageError("disk full")


def _make_content() -> AmbienceContent:
    return AmbienceContent(
        name="Test",
        intension="i",
        publico="p",
        shuffle_rule=False,
        filters=[Filter(genres=["488"])],
    )


def _make_request(prompt: str = "rainy jazz", user_id: str = "u1") -> AmbienceRequest:
    return AmbienceRequest(prompt=prompt, user_id=user_id)


def test_create_returns_ambience() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    result = svc.create(_make_request())
    assert isinstance(result, Ambience)
    assert result.name == "Test"


def test_create_persists_ambience() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    svc.create(_make_request())
    assert len(store.saved) == 1


def test_create_sets_user_id_and_prompt() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    result = svc.create(_make_request(prompt="rainy jazz", user_id="u42"))
    assert result.user_id == "u42"
    assert result.prompt == "rainy jazz"


def test_create_generates_unique_uuids() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request())
    r2 = svc.create(_make_request())
    assert r1.uuid != r2.uuid


def test_fingerprint_is_deterministic() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request(prompt="rainy jazz", user_id="u1"))
    r2 = svc.create(_make_request(prompt="rainy jazz", user_id="u1"))
    assert r1.fingerprint == r2.fingerprint


def test_fingerprint_differs_for_different_users() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request(user_id="u1"))
    r2 = svc.create(_make_request(user_id="u2"))
    assert r1.fingerprint != r2.fingerprint


def test_fingerprint_normalizes_prompt_whitespace() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request(prompt="rainy  jazz"))
    r2 = svc.create(_make_request(prompt="rainy jazz"))
    assert r1.fingerprint == r2.fingerprint


def test_generation_error_propagates() -> None:
    svc = AmbienceService(
        pipeline=_RaisingPipeline(AmbienceGenerationError("bad")),
        store=_FakeStore(),
    )
    with pytest.raises(AmbienceGenerationError):
        svc.create(_make_request())


def test_storage_error_propagates() -> None:
    svc = AmbienceService(
        pipeline=_FakePipeline(_make_content()), store=_FailingStore()
    )
    with pytest.raises(AmbienceStorageError):
        svc.create(_make_request())
