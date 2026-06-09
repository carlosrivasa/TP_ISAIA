from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.ambience import AmbienceContent


@dataclass
class Doc:
    content: str


@dataclass
class LLMRequest:
    system: str
    user: str


class PromptBuilder(Protocol):
    def build(self, prompt: str, context: list[Doc]) -> LLMRequest: ...


class Retriever(Protocol):
    def retrieve(self, prompt: str) -> list[Doc]: ...


class LLMProvider(Protocol):
    def generate(self, req: LLMRequest) -> str: ...


class Pipeline(Protocol):
    def run(self, prompt: str) -> AmbienceContent: ...
