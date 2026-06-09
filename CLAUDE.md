# Ambience — Text-to-Ambience (MVP)

Personal project. A user types a prompt ("rainy afternoon jazz…"), the backend
builds an ambience definition (a JSON structure) via a RAG + LLM pipeline, and
persists it. The frontend renders/visualizes it.

This file is **team-level project memory**. It is loaded into every Claude Code
session in this repo. Keep it short, factual, and current. Component-specific
detail lives in nested `CLAUDE.md` files (see `backend/app/rag/CLAUDE.md`).

---

## Request flow (MVP)

```
User → Frontend (prompt input + visualization)
     → POST /ambiences { prompt, user_id }                 (REST controller — thin)
     → AmbienceService.create()                            (orchestration)
         → RAG: PromptBuilder builds LLM input             (replaceable)
         → LLM: provider returns ambience JSON             (replaceable; Gemini Flash / mock)
         → AmbienceStore.save()                            (replaceable; local files default / OCI bucket)
     → 201 Created  { ambience }  (Location: /ambiences/{id})
```

Two boxes are **explicitly replaceable** and MUST sit behind interfaces:
the **RAG-LLM** pipeline and the **persistence** layer. Default LLM is a **mock**
returning dummy JSON; default persistence is **local JSON files**. Selection is by
configuration, never by editing call sites.

---

## Folder map

```
ambience/
├── CLAUDE.md                  # this file (project memory, team-level)
├── README.md
├── docker-compose.yml
├── .claude/                   # SHARED, COMMITTED Claude Code config (a deliverable)
│   ├── settings.json          # permissions, env (team-shared)
│   ├── rules/                 # code standards, imported into this file (see below)
│   │   ├── code-style.md
│   │   ├── testing.md
│   │   ├── security.md
│   │   └── api.md
│   ├── agents/
│   │   └── rag-researcher.md   # subagent: researches RAG/LLM options for the black box
│   ├── skills/
│   │   └── add-endpoint/SKILL.md
│   └── commands/
│       └── add-endpoint.md     # /add-endpoint — invokes the skill
├── docs/
│   └── plans/                  # plan-mode working docs (point Claude at these)
│       ├── gemini-integration.md
│       └── oci-bucket-integration.md
├── backend/                    # FastAPI service
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py             # app factory, wiring (DI happens here)
│   │   ├── core/               # config/settings, logging
│   │   ├── api/                # routers = controllers. THIN. No business rules.
│   │   │   └── ambiences.py
│   │   ├── services/           # orchestration / use cases
│   │   │   └── ambience_service.py
│   │   ├── models/             # Pydantic schemas (request/response/domain)
│   │   ├── rag/                # ⬛ replaceable RAG-LLM component (own CLAUDE.md)
│   │   │   ├── CLAUDE.md
│   │   │   ├── interfaces.py   # LLMProvider, Retriever, PromptBuilder protocols
│   │   │   ├── pipeline.py
│   │   │   └── providers/      # gemini.py, mock.py
│   │   └── persistence/        # ⬛ replaceable storage component
│   │       ├── interfaces.py   # AmbienceStore protocol
│   │       ├── local_store.py  # default
│   │       └── oci_store.py
│   └── tests/                  # mirrors app/ structure
└── frontend/                   # vanilla HTML/CSS/JS (one view = own .css + .js)
    ├── index.html
    ├── styles.css
    └── app.js
```

> Folders above are the **target** layout. Build them as features land — do not
> scaffold empty files ahead of need.

---

## Conventions (project-level)

- **Stack:** Python 3.12 + FastAPI backend; vanilla HTML/CSS/JS frontend; Docker.
- **Separation of concerns is non-negotiable:**
  - Controllers (`api/`) only parse/validate input, call a service, shape the
    response. **No business logic, no storage, no LLM calls.**
  - Services (`services/`) orchestrate. They depend on **interfaces**, not concretions.
  - Replaceable components (`rag/`, `persistence/`) are reached only through their
    `interfaces.py`. Swapping a provider = config + a new class, never editing callers.
- **Config over code:** LLM provider and storage backend are chosen by env/config.
  See `app/core`. Default: `LLM_PROVIDER=mock`, `STORAGE=local`.
- **HTTP:** create returns `201 Created` with a `Location` header. Validation errors
  `422`, unknown ambience `404`.
- **OpenAPI** is the contract. After any endpoint change, the schema is regenerated
  (see `/add-endpoint`).
- **Detailed standards** live in `.claude/rules/` and are imported below — read them.

## Standards (imported)

@.claude/rules/code-style.md
@.claude/rules/api.md
@.claude/rules/testing.md
@.claude/rules/security.md
@.claude/rules/git.md

---

## Development workflow (superpowers plugin)

This repo enables the **superpowers** plugin (`.claude/settings.json`). Non-trivial
features follow its workflow: **brainstorm → write plan → git worktree → TDD
(red-green-refactor) → code review → finish branch**. Skills self-activate; let
them. Note: superpowers favors frequent autonomous commits, but our
`.claude/rules/git.md` takes precedence — **ask before commits, branches, and
pushes**, and use the user's commit message.

## Working agreements for Claude

- Ask before installing dependencies or running mutating commands (enforced by
  `.claude/settings.json`).
- Keep functions small (see code-style rule). Prefer composition + interfaces.
- When touching the RAG-LLM box, the nested `backend/app/rag/CLAUDE.md` applies.
- Never commit secrets. `.env` is git-ignored and read-blocked for Claude.
