# RAG-LLM component (the replaceable "black box")

> Nested memory: this file auto-loads **only when working inside `backend/app/rag/`**.
> It extends the root `CLAUDE.md` and the `.claude/rules/` standards. This is the
> heaviest component for the MVP and beyond — treat its boundary as sacred.

## Purpose

Turn a user `prompt` into a **validated ambience JSON**. The whole component is one
swappable box: today a mock returns dummy JSON; tomorrow a RAG retriever + Gemini
Flash do the real work. Callers (the `AmbienceService`) must not know or care which.

```
prompt ─▶ PromptBuilder ─▶ (Retriever: optional context) ─▶ LLMProvider ─▶ raw JSON
                                                                  └─▶ schema-validate ─▶ Ambience
```

## Interfaces (the contract — keep stable)

Defined in `interfaces.py` as `typing.Protocol`s. Everything else is an implementation.

- `PromptBuilder.build(prompt: str, context: list[Doc]) -> LLMRequest`
  Builds provider-agnostic input. **Owns the prompt logic** that varies per LLM —
  this is the part that gets replaced when the LLM changes.
- `Retriever.retrieve(prompt: str) -> list[Doc]`
  Optional RAG context. MVP can return `[]` (no retrieval) behind the same interface.
- `LLMProvider.generate(req: LLMRequest) -> str`
  Calls the model, returns raw text/JSON. Implementations: `MockProvider` (default),
  `GeminiProvider`.
- The component's public entrypoint is `pipeline.py::AmbiencePipeline.run(prompt) -> Ambience`,
  which composes the three and **validates output against the `Ambience` Pydantic
  schema** before returning.

## Rules specific to this box

1. **Nothing leaks out except `Ambience` (validated) or a typed error.** No provider
   SDK types, no raw dicts, no HTTP objects cross the boundary.
2. **The LLM output is untrusted.** Always parse + validate against the schema. On
   invalid JSON: one bounded retry/repair, then raise `AmbienceGenerationError`.
3. **Provider selection is config-driven** (`LLM_PROVIDER`, `RETRIEVER`), resolved at
   the composition root. No `if provider == "gemini"` branching in business code.
4. **PromptBuilder is per-LLM.** When swapping models, you replace the builder +
   provider together; the interface and the service stay untouched.
5. Keep prompt templates as data (files/constants), not buried in code paths.

## MVP vs post-MVP

- **MVP:** `MockProvider` + no-op `Retriever`. Lock the `Ambience` schema and the
  three interfaces first — everything downstream depends on the schema being stable.
- **Post-MVP:** real `GeminiProvider` (Gemini Flash) — see
  `docs/plans/gemini-integration.md`; real retrieval (embeddings + vector store);
  prompt evaluation harness; caching of generations.

## When changing this component

- Changing the `Ambience` schema is a breaking change — update the schema, the mock,
  all providers, and tests together; note it in the commit.
- New provider → implement the Protocol, add conformance tests (see testing rule),
  register it in config. Do not touch callers.
- Need options/background on RAG approaches? Use the **`rag-researcher`** subagent.
