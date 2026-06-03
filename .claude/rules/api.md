# API & REST rules

Scope: the FastAPI backend under `backend/app/api`. This is the
**path-scoped rule** for the HTTP layer — keep controllers honest.

## Resource conventions
- Resources are plural nouns: `/ambiences`, `/ambiences/{id}`.
- Verbs live in the HTTP method, not the path. No `/createAmbience`.

## Status codes
- `POST /ambiences` → **`201 Created`**, body = created ambience, header
  `Location: /ambiences/{id}`.
- `GET` existing → `200`; missing → `404`.
- Invalid/malformed body → `422` (FastAPI/Pydantic default — let it work).
- Downstream LLM/storage failure the client can't fix → `502`/`503` with a
  problem body, never a raw stack trace.

## Contracts & schemas
- Request and response bodies are **Pydantic models** in `app/models`, never raw
  dicts. The model IS the documented contract.
- Every route declares `response_model` and explicit `status_code`.
- `POST /ambiences` request: `{ "prompt": str, "user_id": str }`.

## OpenAPI is the source of truth
- The committed `backend/openapi.yaml` (or `.json`) is regenerated after **any**
  route/model change. Use `/add-endpoint` — it regenerates + tests.
- Breaking changes to an existing contract require a note in the PR/commit body.

## Controller discipline
- A handler: validate (via the Pydantic model) → call one service method → return.
- No business logic, no `await store...`, no LLM calls in the handler.
- Inject dependencies (service, store) via FastAPI `Depends`, resolved at the
  composition root — so tests can inject fakes.

## Versioning (post-MVP)
- When the contract stabilizes, prefix with `/v1`. Not required for the MVP.
