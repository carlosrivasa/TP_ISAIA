import json

from app.models.ambience import AmbienceContent
from app.rag.interfaces import Doc, LLMRequest
from app.rag.providers.mock import MockPromptBuilder, MockProvider, NoOpRetriever


def test_no_op_retriever_returns_empty():
    r = NoOpRetriever()
    result = r.retrieve("any prompt")
    assert result == []


def test_mock_prompt_builder_returns_llm_request():
    b = MockPromptBuilder()
    req = b.build("rainy jazz", [])
    assert isinstance(req, LLMRequest)
    assert "rainy jazz" in req.user


def test_mock_prompt_builder_ignores_context():
    b = MockPromptBuilder()
    req_no_ctx = b.build("test", [])
    req_with_ctx = b.build("test", [Doc(content="extra context")])
    assert req_no_ctx.user == req_with_ctx.user


def test_mock_provider_returns_valid_json():
    p = MockProvider()
    raw = p.generate(LLMRequest(system="", user="test"))
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_mock_provider_output_validates_as_ambience_content():
    p = MockProvider()
    raw = p.generate(LLMRequest(system="", user="test"))
    content = AmbienceContent.model_validate_json(raw)
    assert len(content.name) > 0
    assert len(content.filters) >= 1


def test_mock_provider_is_deterministic():
    p = MockProvider()
    req = LLMRequest(system="", user="anything")
    assert p.generate(req) == p.generate(req)
