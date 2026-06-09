from __future__ import annotations

import json

from app.models.ambience import AmbienceContent
from app.models.errors import AmbienceGenerationError
from app.rag.interfaces import LLMProvider, PromptBuilder, Retriever


class AmbiencePipeline:
    def __init__(
        self,
        provider: LLMProvider,
        retriever: Retriever,
        builder: PromptBuilder,
    ) -> None:
        self._provider = provider
        self._retriever = retriever
        self._builder = builder

    def run(self, prompt: str) -> AmbienceContent:
        context = self._retriever.retrieve(prompt)
        req = self._builder.build(prompt, context)
        raw = self._provider.generate(req)
        return self._validate(raw)

    def _validate(self, raw: str) -> AmbienceContent:
        try:
            data = json.loads(raw)
            return AmbienceContent.model_validate(data)
        except Exception as exc:
            raise AmbienceGenerationError(f"Invalid LLM output: {exc}") from exc
