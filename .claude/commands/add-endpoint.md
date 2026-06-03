---
description: Scaffold/modify a backend endpoint end-to-end (models, controller, service, tests, OpenAPI regen)
argument-hint: <method> <path> — e.g. POST /ambiences
---

Run the **add-endpoint** skill to add or change this endpoint across every layer,
following `.claude/rules/api.md`, `code-style.md`, and `testing.md`.

Target endpoint: $ARGUMENTS

Steps: define Pydantic models → thin controller → service (behind interfaces) →
tests (fakes, no real Gemini/OCI) → regenerate committed `backend/openapi.yaml` →
run ruff + mypy + pytest and report results. Keep the controller free of business
logic. If the endpoint's purpose or contract is unclear, ask me before generating.
