# Slice 1 — Ambience Skeleton (end-to-end MVP) — Design

- **Date:** 2026-06-09
- **Status:** Approved (pending spec review)
- **Scope:** First vertical slice of the Text-to-Ambience MVP.

---

## 1. Context

A user types a free-text prompt; the backend turns it into a structured **ambience**
(a music-curation recipe of filters) and persists it. The real downstream client is
WordPress (ambiences are `ps_ambience` posts driving a track player), but this slice
writes **our own JSON**, not WP.

This is **Slice 1 of a larger decomposition**:

1. **Slice 1 (this doc)** — end-to-end skeleton: prompt → API → mock RAG-LLM →
   validate → local JSON → render. No cloud, no secrets, no WP.
2. Slice 1.5 — `GET /ambiences/{id}`.
3. Later — real Gemini provider; real RAG retriever (WP vocab); WP data-access
   service + track playlist; WP write-back adapter; OCI storage.

## 2. Goal & non-goals

**Goal:** a working, tested, end-to-end path that exercises every layer and leaves
every replaceable box behind an interface, swappable by config.

**Non-goals (explicit seams left clean):**
- `GET`/list endpoints (Slice 1.5).
- Real Gemini provider (`docs/plans/gemini-integration.md`).
- Real Retriever reading WP DB + local vocab files (genre IDs↔names, moods, regions,
  decades) — the RAG slice; also unlocks frontend ID→name labels.
- WP data-access service (ambiences, user profile, schedules, tracks) + track-matching
  playlist.
- WP write-back adapter (clean JSON → `ps_ambience` meta).
- OCI bucket store (`docs/plans/oci-bucket-integration.md`).
- Redis-backed rate limiter; multiple-filter generation; time-bucket fingerprint.
- **Auth:** `user_id` is trusted request input for the MVP (known gap).

## 3. Domain model (clean domain JSON, Pydantic v2)

The LLM box produces **content only**; the service owns **identity/metadata**. Two models:

```jsonc
// Produced & validated from the LLM/mock output:
AmbienceContent {
  name: str
  intension: str
  publico: str
  shuffle_rule: bool
  filters: Filter[]      // >= 1; Slice 1 produces exactly one
}

// Stored & returned (service assembles from AmbienceContent + metadata):
Ambience {
  uuid: str              // server-generated uuid4 (NOT the WP post id)
  user_id: str           // from request
  prompt: str            // original free-text, echoed & stored
  fingerprint: str       // deterministic hash(user_id + normalized prompt)
  created_at: datetime
  name, intension, publico, shuffle_rule, filters   // from AmbienceContent
}

Filter {
  shuffle_rule: bool
  genres: str[]                 // genre IDs, e.g. "488"
  moods: str[]                  // mood names, e.g. "Cool"
  album_release_dates: str[]    // decades, e.g. "2010s"
  artist_origin_regions: str[]
  artist_origin_countries: str[]
  explicit: bool
  tracks_exceptions: str[]
  // audio features, each an optional range:
  popularity, acousticness, danceability, energy, instrumentalness,
  liveness, loudness, speechiness, tempo, valence : Range
}

Range { min: number | null, max: number | null }
```

**Validation (MVP):**
- `name` required & non-empty; `filters` length >= 1.
- Lists default to `[]`; `explicit`/`shuffle_rule` default `false`.
- Each `Range` optional; if both bounds present, enforce `min <= max`. Units vary
  (most 0–100, `tempo` BPM, `loudness` dB); MVP validates ordering only, not domain.
- The **same `AmbienceContent` schema validates the LLM/mock output before persisting**
  (untrusted-output rule).

**Identity:**
- `uuid` (random uuid4) = stable, fetchable storage identity. Renamed from `id` to
  avoid confusion with the WP post id.
- `fingerprint` = deterministic `hash(user_id + normalized_prompt)`, where
  *normalized* = trimmed, lower-cased, internal whitespace collapsed (sha256 hex).
  Stored, but **no
  behavior wired onto it yet** — future hook for dedup/caching/"you've made this
  before", and a place to fold a time bucket for time-aware variation later.

## 4. Architecture

All replaceable boxes sit behind `typing.Protocol`s; concretes are wired at the
composition root, selected by config. Business code never instantiates a concrete.

```
api/ambiences.py        POST /ambiences -> validate -> service.create() -> 201 + Location
services/ambience_service.py   orchestration (section 5)
rag/
  interfaces.py         PromptBuilder, Retriever, LLMProvider   (Protocols)
  pipeline.py           AmbiencePipeline.run(prompt) -> AmbienceContent  (composes + validates)
  providers/mock.py     MockProvider -> canned, valid AmbienceContent JSON (deterministic)
persistence/
  interfaces.py         AmbienceStore   (Protocol)
  local_store.py        save(ambience) -> DATA_DIR/{uuid}.json
ratelimit/
  interfaces.py         RateLimiter   (Protocol)
  in_memory.py          fixed-window per user_id
models/                 request + AmbienceContent + Ambience + Filter + Range
core/config.py          settings (LLM_PROVIDER, STORAGE, RATE_LIMIT_PER_MINUTE, DATA_DIR, CORS, prompt caps)
main.py                 composition root: pick provider/store/limiter by config, wire Depends
```

Interfaces:
- `LLMProvider.generate(req: LLMRequest) -> str`
- `Retriever.retrieve(prompt: str) -> list[Doc]` (Slice 1: returns `[]`)
- `PromptBuilder.build(prompt: str, context: list[Doc]) -> LLMRequest`
- `AmbienceStore.save(ambience: Ambience) -> None`
- `RateLimiter.check(user_id: str) -> None` (raises `RateLimitExceeded`)

## 5. Request flow — `service.create(request)`

1. `retriever.retrieve(prompt)` → `[]` (seam for WP-vocab RAG).
2. `prompt_builder.build(prompt, context)` → provider-agnostic `LLMRequest`.
3. `llm.generate(req)` → raw JSON string.
4. Validate raw → `AmbienceContent` (untrusted-output gate).
5. Assemble `Ambience`: add `uuid` (uuid4), `user_id`, `prompt`,
   `fingerprint = hash(user_id + normalized prompt)`, `created_at`.
6. `store.save(ambience)` → write `{uuid}.json` (filename from server `uuid` only —
   no path traversal from user input).
7. Return `Ambience`.

The `RateLimiter.check(user_id)` runs as a FastAPI dependency **before** the service,
so a throttled request never reaches the LLM.

## 6. API contract

- **`POST /ambiences`**
  - Request: `{ "prompt": str, "user_id": str }`
    - `prompt`: `min_length=3`, `max_length=2000` (configurable).
  - Success: **`201 Created`**, body = `Ambience`, header `Location: /ambiences/{uuid}`.
  - Declares `response_model=Ambience`, explicit `status_code=201`.

## 7. Error handling

| Condition | Where | → Status | Notes |
|---|---|---|---|
| Malformed/missing body | Pydantic request model | `422` | automatic |
| Prompt too long/short | `Field(min/max_length)` | `422` | matches frontend cap |
| User over our rate limit | `RateLimiter` dep (per `user_id`) | `429` | + `Retry-After` |
| LLM output invalid / fails schema | pipeline validation | `502` | `AmbienceGenerationError` |
| LLM upstream rate-limited (Gemini 429) | provider | `503` | `LLMRateLimitError` + `Retry-After` |
| LLM timeout / down | provider | `502`/`503` | |
| Storage failure | store | `503` | `AmbienceStorageError` |

**Two distinct 429-ish cases, deliberately split:**
- `429` = *our* user exceeded *our* limit (their fault → slow down).
- `503` + `Retry-After` = *Gemini* rate-limited *us* (not the user's fault; retry later).

All client-facing errors are sanitized problem responses; details logged server-side only.

**Slice 1 reality check:** rate limiter (`429`) and length caps are **live** now.
`LLMRateLimitError → 503` is *defined* now (typed error + mapping) but only *fires*
with the real Gemini provider; the mock never raises it.

## 8. Frontend (vanilla, separate static app)

Throwaway demo/harness that hits the real API exactly as WordPress later will
(separate origin, `fetch`, CORS).

- `index.html` — prompt `<textarea>` (`maxlength=2000` + live counter), help text
  encouraging the user to describe **intention** and **audience**, Submit, result
  panel, error region.
- `styles.css` — layout, chips, range bars.
- `app.js` — `POST /ambiences`, manage state, render `Ambience`.

**Render (structured read-only + "view raw JSON" toggle):**
- Header: `name`; `intension` + `publico` paragraphs; `shuffle_rule` badge.
- Per filter: `genres`/`moods`/`album_release_dates`/`artist_origin_*` as chips;
  `explicit` badge; audio-feature `Range`s as labeled min–max (empty ranges hidden).
- Metadata footer: `uuid`, `fingerprint`, `created_at`.
- Note: mock returns `genres` as **IDs**; no name lookup until RAG vocab — Slice 1
  chips show IDs.

**UX:** Submit disabled + spinner while in flight (soft throttle). Error copy mapped
from status (`422` → check prompt; `429` → "try again in Ns" via `Retry-After`;
`502/503` → service busy).

**Config/serving:** API base URL a configurable constant in `app.js` (default
`http://localhost:8000`). Plain static files; `docker-compose` runs backend (uvicorn)
+ a static server. No build step. Backend CORS restricted to the frontend origin.

## 9. Testing strategy

Fakes for every interface; no real network or data dir; deterministic.

1. **Controller contract** (`TestClient` + fake service): `201` + `Location`, response
   shape, `422` (missing/oversized), `429` + `Retry-After` (fake limiter trips),
   `502`/`503` (fake service raises typed errors).
2. **Service orchestration** (all interfaces faked): builds prompt → calls provider →
   validates → assembles metadata → persists. Asserts `fingerprint` determinism and
   `uuid` uniqueness.
3. **Interface conformance:** `MockProvider` emits schema-valid `AmbienceContent`;
   `LocalStore` round-trips via `tmp_path`; `RateLimiter` allows N then blocks;
   `Retriever` returns `[]`.
4. **Schema/validation:** `Range` `min <= max`; required `name`; list defaults;
   invalid LLM output rejected.

Definition of done: `pytest` + `ruff` + `mypy` all green.

## 10. Known gaps / open questions

- `user_id` is unauthenticated/trusted input (auth is a later slice).
- In-memory rate limiter does not survive restarts or span workers (Redis later).
- Genre IDs shown without names until the RAG vocab retriever exists.
- Real LLM determinism vs `fingerprint` semantics to be revisited when Gemini lands.
