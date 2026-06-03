---
name: add-endpoint
description: >-
  Use when adding or changing a REST endpoint in the FastAPI backend. Ensures the
  full contract is updated together: Pydantic models, thin controller, service
  method behind interfaces, tests, and a regenerated committed OpenAPI spec.
  Triggers: "add an endpoint", "new route", "expose X over HTTP", /add-endpoint.
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# Add / change a backend endpoint

Drive a new or changed endpoint through every layer so nothing is left inconsistent.
Follow `.claude/rules/api.md`, `code-style.md`, and `testing.md`. Confirm the
endpoint's purpose with the user if it is ambiguous before generating files.

## Checklist (do in order)

1. **Define the contract first.** Add/adjust request + response **Pydantic models**
   in `backend/app/models/`. The model is the contract — no raw dicts.
2. **Controller (thin).** Add the route in `backend/app/api/<resource>.py`:
   validate via the model → call **one** service method → return with the correct
   status code (`POST` create → `201` + `Location` header). No business logic, no
   storage/LLM calls here. Inject the service via `Depends`.
3. **Service / orchestration.** Add the use-case method in
   `backend/app/services/`. It depends on **interfaces**, not concrete providers.
4. **Wiring.** If a new dependency is introduced, wire it at the composition root
   (`app/main.py` / `app/core`), selected by config — not in the handler.
5. **Tests** (`backend/tests/`, mirroring `app/`):
   - controller: status code, response shape, `Location` header, `422` on bad input,
     with a **fake service** injected;
   - service: orchestration with **fakes for interfaces** (no real Gemini/OCI).
6. **Regenerate OpenAPI.** Export the live schema to the committed
   `backend/openapi.yaml`:
   ```bash
   cd backend && python -c "import json,yaml; from app.main import app; \
   print(yaml.safe_dump(app.openapi(), sort_keys=False))" > openapi.yaml
   ```
   (Adjust the import path to the actual app factory.)
7. **Verify.** Run `ruff`, `mypy`, `pytest`. Report results honestly — if anything
   fails or was skipped, say so.

## Done means
Models + thin controller + service + tests + regenerated `openapi.yaml`, all checks
green, no business logic leaked into the controller. Summarize what changed and the
new contract.
