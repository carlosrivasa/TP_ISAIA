# Testing rules

## Framework & layout
- `pytest`. Tests live in `backend/tests/` and **mirror** `app/` (e.g.
  `tests/services/test_ambience_service.py`).
- One behavior per test. Name tests by behavior:
  `test_create_returns_201_with_location_header`.

## What to test (MVP priorities)
1. **Controller contract**: status codes, response shape, `Location` header,
   `422` on bad input. Use FastAPI `TestClient` with fake service injected.
2. **Service orchestration**: that it builds the prompt, calls the LLM provider,
   and persists — using **fakes for the interfaces**, not real Gemini/OCI.
3. **Interface conformance**: every provider (mock, gemini) and every store
   (local, oci) satisfies its Protocol and round-trips a known ambience.

## How
- **Never call real external services in tests.** Gemini and OCI are stubbed via
  their interfaces. This is the payoff of programming to interfaces.
- Filesystem store: use `tmp_path`; never write to the real data folder.
- Deterministic: no real network, no sleeps, no wall-clock assertions.
- Fast: the suite runs in seconds. Slow/integration tests get a
  `@pytest.mark.integration` marker and are opt-in.

## Definition of done for a change
- New/changed endpoint → controller + service tests added or updated.
- `pytest`, `ruff`, and `mypy` all green. State the result honestly; if something
  fails or was skipped, say so.
