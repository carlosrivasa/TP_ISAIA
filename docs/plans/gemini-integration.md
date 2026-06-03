# Plan: Connect the real Gemini Flash LLM provider

> A **plan-mode working doc**, not runnable config. Point Claude at this file and
> enter plan mode (Shift+Tab) when ready to implement. Keep it updated as decisions land.

## Goal
Replace `MockProvider` with a real `GeminiProvider` (Gemini Flash) implementing the
`LLMProvider` Protocol, selectable via `LLM_PROVIDER=gemini`. Zero changes to
`AmbienceService` or controllers.

## Definition of done
- `GeminiProvider.generate(req) -> str` returns ambience JSON that validates against
  the `Ambience` schema; mock still works; switch is pure config.
- Secrets via env only; no key in code/logs. Tests stub the SDK (no real calls in CI).

## Pre-work / open questions
- [ ] Confirm SDK/auth approach and exact model id (use `rag-researcher` subagent).
- [ ] API key acquisition + where it lives (`.env`, `GEMINI_API_KEY`), add to `.env.example`.
- [ ] How do we force structured JSON output (response schema / JSON mode) reliably?
- [ ] Timeout, retry, and cost/latency budget per request.

## Steps (fill in during planning)
1. Add `GEMINI_API_KEY` + `LLM_PROVIDER` to config (`app/core`); update `.env.example`.
2. Implement `providers/gemini.py` against the `LLMProvider` Protocol.
3. Update `PromptBuilder` for Gemini's structured-output format (per-LLM, as designed).
4. Validate output against `Ambience`; one bounded repair/retry, then raise.
5. Conformance + error-path tests with the SDK stubbed.
6. Register provider in the composition root; document the switch in README.

## Risks
- Output not valid JSON → must rely on schema validation + repair, never trust raw.
- Rate limits / cost on real traffic.
- Prompt injection via user prompt — keep system vs user content separated (security rule).
