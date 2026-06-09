import json

import pytest

from app.models.ambience import AmbienceContent
from app.models.errors import AmbienceGenerationError
from app.rag.interfaces import Doc, LLMRequest
from app.rag.pipeline import AmbiencePipeline


class _FakeProvider:
    def __init__(self, raw: str) -> None:
        self._raw = raw

    def generate(self, req: LLMRequest) -> str:
        return self._raw


class _FakeBuilder:
    def build(self, prompt: str, context: list[Doc]) -> LLMRequest:
        return LLMRequest(system="", user=prompt)


class _FakeRetriever:
    def retrieve(self, prompt: str) -> list[Doc]:
        return [Doc(content="context")]


_VALID_CONTENT = json.dumps(
    {
        "name": "Test",
        "intension": "i",
        "publico": "p",
        "shuffle_rule": False,
        "filters": [{}],
    }
)


def _make_pipeline(raw: str) -> AmbiencePipeline:
    return AmbiencePipeline(
        provider=_FakeProvider(raw),
        retriever=_FakeRetriever(),
        builder=_FakeBuilder(),
    )


def test_run_returns_ambience_content() -> None:
    pipeline = _make_pipeline(_VALID_CONTENT)
    result = pipeline.run("some prompt")
    assert isinstance(result, AmbienceContent)
    assert result.name == "Test"


def test_run_passes_prompt_to_builder() -> None:
    received: list[str] = []

    class _CapturingBuilder:
        def build(self, prompt: str, context: list[Doc]) -> LLMRequest:
            received.append(prompt)
            return LLMRequest(system="", user=prompt)

    pipeline = AmbiencePipeline(
        provider=_FakeProvider(_VALID_CONTENT),
        retriever=_FakeRetriever(),
        builder=_CapturingBuilder(),
    )
    pipeline.run("hello world")
    assert received == ["hello world"]


def test_invalid_json_raises_generation_error() -> None:
    pipeline = _make_pipeline("not json at all")
    with pytest.raises(AmbienceGenerationError):
        pipeline.run("prompt")


def test_invalid_schema_raises_generation_error() -> None:
    bad = json.dumps({"name": "", "intension": "i", "publico": "p", "filters": []})
    pipeline = _make_pipeline(bad)
    with pytest.raises(AmbienceGenerationError):
        pipeline.run("prompt")
