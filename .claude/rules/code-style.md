# Code style & design rules

These are hard standards for this repo. They apply everywhere; the RAG component
adds more in `backend/app/rag/CLAUDE.md`.

## Functions & size
- **A function does one thing.** Target ≤ 20 lines of logic (excluding signature,
  docstring, blank lines). If you need a comment to explain a block, extract it.
- Max 3 positional parameters. More → pass an object / dataclass / Pydantic model.
- Cyclomatic simplicity: avoid nesting deeper than 2 levels — use early returns
  and guard clauses.

## Naming
- Reveal intent. `build_prompt`, not `process`. No abbreviations except well-known
  ones (`id`, `db`, `llm`).
- Booleans read as predicates: `is_persisted`, `has_retriever`.

## Separation of concerns (enforced)
- **Controllers (`api/`)**: parse input, call one service method, map to a response.
  No business rules, no I/O to storage or LLM. If a controller is longer than a
  screen, logic leaked in — move it to a service.
- **Services (`services/`)**: orchestrate use cases. Depend on **interfaces**, never
  on concrete providers or frameworks. No `fastapi` imports here.
- **Components (`rag/`, `persistence/`)**: only reachable through their
  `interfaces.py`. Implementations are interchangeable.
- **Frontend**: each view owns its markup, style, and behavior in separate files
  (`index.html` + `styles.css` + `app.js`). No inline `<style>`/`<script>` blocks,
  no business logic in the view beyond rendering + calling the API.

## Interfaces & replaceability
- Anything described as "replaceable" or a "black box" MUST sit behind a Python
  `Protocol` (preferred) or ABC. Concrete classes implement it; callers type-hint
  the interface.
- Wiring/instantiation happens at the composition root (`app/main.py` /
  `app/core`), selected by config. Business code never does `GeminiProvider()`
  directly.
- Program to the interface so a box can be swapped with zero changes to its callers.

## Clean code
- No dead code, no commented-out blocks, no TODO without an owner/context.
- Prefer pure functions; isolate side effects (I/O, network) at the edges.
- Errors are explicit: raise typed/domain exceptions, don't return sentinels.
- DRY, but don't over-abstract before the second real use case.

## Python specifics
- Type hints on every public function. Pydantic v2 for data at boundaries.
- `ruff` for lint+format, `mypy` for types. Code must pass both before "done".
- Imports ordered stdlib / third-party / local. No wildcard imports.
