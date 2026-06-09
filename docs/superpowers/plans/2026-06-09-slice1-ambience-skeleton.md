# Slice 1 — Ambience Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working, tested, end-to-end path — prompt → `POST /ambiences` → mock RAG-LLM → validated `Ambience` JSON → local file store → `201 Created` → vanilla frontend renders it.

**Architecture:** Clean layered FastAPI backend where every replaceable box (LLM provider, retriever, prompt builder, store, rate limiter) sits behind a `typing.Protocol`; the composition root wires concretions by config. The frontend is a separate static app calling the API with `fetch`, mirroring how WordPress will call it later.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic v2, pydantic-settings, pytest, httpx, ruff, mypy, PyYAML; vanilla HTML/CSS/JS frontend; nginx (docker-compose static server); Docker.

---

## File map (every file this plan creates)

```
backend/
  pyproject.toml
  app/
    __init__.py
    main.py                          # app factory + composition root + error handlers
    core/
      __init__.py
      config.py                      # Settings via pydantic-settings
    models/
      __init__.py
      ambience.py                    # Range, Filter, AmbienceContent, AmbienceRequest, Ambience
      errors.py                      # domain exceptions
    rag/
      __init__.py
      interfaces.py                  # Doc, LLMRequest, Pipeline, PromptBuilder, Retriever, LLMProvider (Protocols)
      pipeline.py                    # AmbiencePipeline — composes + validates LLM output
      providers/
        __init__.py
        mock.py                      # MockProvider, MockPromptBuilder, NoOpRetriever
    persistence/
      __init__.py
      interfaces.py                  # AmbienceStore Protocol
      local_store.py                 # LocalStore — saves {uuid}.json to DATA_DIR
    ratelimit/
      __init__.py
      interfaces.py                  # RateLimiter Protocol
      in_memory.py                   # InMemoryRateLimiter — fixed-window per user_id
    services/
      __init__.py
      ambience_service.py            # AmbienceService.create()
    api/
      __init__.py
      ambiences.py                   # POST /ambiences router
  tests/
    __init__.py
    conftest.py                      # shared fixtures
    models/
      __init__.py
      test_ambience.py
    rag/
      __init__.py
      test_pipeline.py
      providers/
        __init__.py
        test_mock.py
    persistence/
      __init__.py
      test_local_store.py
    ratelimit/
      __init__.py
      test_in_memory.py
    services/
      __init__.py
      test_ambience_service.py
    api/
      __init__.py
      test_ambiences.py
  openapi.yaml                       # generated — do not hand-edit
frontend/
  index.html
  styles.css
  app.js
backend/Dockerfile
docker-compose.yml
```

---

## Task 1: Project bootstrap

**Files:**
- Create: `backend/pyproject.toml`
- Create: all `__init__.py` stubs listed in the file map
- Create: `backend/app/core/__init__.py`, etc.

- [ ] **Step 1: Create the backend directory structure**

```bash
mkdir -p backend/app/core backend/app/models \
  backend/app/rag/providers backend/app/persistence \
  backend/app/ratelimit backend/app/services backend/app/api \
  backend/tests/models backend/tests/rag/providers \
  backend/tests/persistence backend/tests/ratelimit \
  backend/tests/services backend/tests/api \
  frontend
```

- [ ] **Step 2: Create all empty `__init__.py` files**

```bash
touch backend/app/__init__.py \
  backend/app/core/__init__.py \
  backend/app/models/__init__.py \
  backend/app/rag/__init__.py \
  backend/app/rag/providers/__init__.py \
  backend/app/persistence/__init__.py \
  backend/app/ratelimit/__init__.py \
  backend/app/services/__init__.py \
  backend/app/api/__init__.py \
  backend/tests/__init__.py \
  backend/tests/models/__init__.py \
  backend/tests/rag/__init__.py \
  backend/tests/rag/providers/__init__.py \
  backend/tests/persistence/__init__.py \
  backend/tests/ratelimit/__init__.py \
  backend/tests/services/__init__.py \
  backend/tests/api/__init__.py
```

- [ ] **Step 3: Write `backend/pyproject.toml`**

```toml
[project]
name = "ambience-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "pyyaml>=6.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

- [ ] **Step 4: Install dependencies with uv**

```bash
cd backend && uv sync
```

Expected: uv creates `.venv/` and `uv.lock`. No errors.

- [ ] **Step 5: Verify tooling works**

```bash
cd backend && uv run python --version
```

Expected: `Python 3.12.x`

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/app backend/tests
git commit -m "chore: bootstrap backend project with uv"
```

---

## Task 2: Domain models

**Files:**
- Create: `backend/app/models/ambience.py`
- Create: `backend/tests/models/test_ambience.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/models/test_ambience.py`:
```python
import pytest
from pydantic import ValidationError
from app.models.ambience import (
    Ambience,
    AmbienceContent,
    AmbienceRequest,
    Filter,
    Range,
)
from datetime import datetime, timezone


def test_range_valid_min_max():
    r = Range(min=10.0, max=50.0)
    assert r.min == 10.0
    assert r.max == 50.0


def test_range_min_gt_max_raises():
    with pytest.raises(ValidationError):
        Range(min=80.0, max=20.0)


def test_range_defaults_to_none():
    r = Range()
    assert r.min is None
    assert r.max is None


def test_range_only_min():
    r = Range(min=40.0)
    assert r.min == 40.0
    assert r.max is None


def test_filter_defaults():
    f = Filter()
    assert f.genres == []
    assert f.moods == []
    assert f.explicit is False
    assert f.shuffle_rule is False
    assert f.tracks_exceptions == []
    assert f.popularity == Range()


def test_ambience_content_requires_name():
    with pytest.raises(ValidationError):
        AmbienceContent(
            name="",
            intension="x",
            publico="x",
            shuffle_rule=False,
            filters=[Filter()],
        )


def test_ambience_content_requires_at_least_one_filter():
    with pytest.raises(ValidationError):
        AmbienceContent(
            name="My Ambience",
            intension="x",
            publico="x",
            shuffle_rule=False,
            filters=[],
        )


def test_ambience_content_valid():
    content = AmbienceContent(
        name="Workout Mix",
        intension="High energy",
        publico="Gym-goers",
        shuffle_rule=True,
        filters=[Filter(genres=["488"], moods=["Lively"])],
    )
    assert content.name == "Workout Mix"
    assert len(content.filters) == 1


def test_ambience_request_too_short():
    with pytest.raises(ValidationError):
        AmbienceRequest(prompt="ab", user_id="u1")


def test_ambience_request_too_long():
    with pytest.raises(ValidationError):
        AmbienceRequest(prompt="x" * 2001, user_id="u1")


def test_ambience_request_valid():
    req = AmbienceRequest(prompt="rainy afternoon jazz", user_id="u1")
    assert req.user_id == "u1"


def test_ambience_round_trips_json():
    a = Ambience(
        uuid="test-uuid",
        user_id="u1",
        prompt="rainy afternoon jazz",
        fingerprint="abc123",
        created_at=datetime(2026, 6, 9, tzinfo=timezone.utc),
        name="Jazz",
        intension="Relaxed",
        publico="Everyone",
        shuffle_rule=False,
        filters=[Filter()],
    )
    data = a.model_dump_json()
    b = Ambience.model_validate_json(data)
    assert b.uuid == a.uuid
    assert b.fingerprint == a.fingerprint
```

- [ ] **Step 2: Run tests — expect failures (models don't exist yet)**

```bash
cd backend && uv run pytest tests/models/test_ambience.py -v
```

Expected: `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement `backend/app/models/ambience.py`**

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class Range(BaseModel):
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def _validate_order(self) -> Range:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must be <= max")
        return self


class Filter(BaseModel):
    shuffle_rule: bool = False
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    album_release_dates: list[str] = Field(default_factory=list)
    artist_origin_regions: list[str] = Field(default_factory=list)
    artist_origin_countries: list[str] = Field(default_factory=list)
    explicit: bool = False
    tracks_exceptions: list[str] = Field(default_factory=list)
    popularity: Range = Field(default_factory=Range)
    acousticness: Range = Field(default_factory=Range)
    danceability: Range = Field(default_factory=Range)
    energy: Range = Field(default_factory=Range)
    instrumentalness: Range = Field(default_factory=Range)
    liveness: Range = Field(default_factory=Range)
    loudness: Range = Field(default_factory=Range)
    speechiness: Range = Field(default_factory=Range)
    tempo: Range = Field(default_factory=Range)
    valence: Range = Field(default_factory=Range)


class AmbienceContent(BaseModel):
    name: str = Field(min_length=1)
    intension: str
    publico: str
    shuffle_rule: bool = False
    filters: list[Filter] = Field(min_length=1)


class AmbienceRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    user_id: str = Field(min_length=1)


class Ambience(BaseModel):
    uuid: str
    user_id: str
    prompt: str
    fingerprint: str
    created_at: datetime
    name: str
    intension: str
    publico: str
    shuffle_rule: bool
    filters: list[Filter]
```

- [ ] **Step 4: Run tests — expect green**

```bash
cd backend && uv run pytest tests/models/test_ambience.py -v
```

Expected: all 13 tests PASS.

- [ ] **Step 5: Run ruff and mypy**

```bash
cd backend && uv run ruff check app/models/ambience.py && uv run mypy app/models/ambience.py
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/ambience.py backend/tests/models/test_ambience.py
git commit -m "feat: add domain models (Range, Filter, AmbienceContent, Ambience)"
```

---

## Task 3: Domain exceptions + RAG interfaces

**Files:**
- Create: `backend/app/models/errors.py`
- Create: `backend/app/rag/interfaces.py`

No TDD for these files — they are pure type definitions with no behavior to test in isolation. Their correctness is validated indirectly by the tests in every subsequent task.

- [ ] **Step 1: Write `backend/app/models/errors.py`**

```python
class AmbienceGenerationError(Exception):
    pass


class AmbienceStorageError(Exception):
    pass


class LLMRateLimitError(Exception):
    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(f"LLM rate limited; retry after {retry_after}s")


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded; retry after {retry_after}s")
```

- [ ] **Step 2: Write `backend/app/rag/interfaces.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.ambience import AmbienceContent


@dataclass
class Doc:
    content: str


@dataclass
class LLMRequest:
    system: str
    user: str


class PromptBuilder(Protocol):
    def build(self, prompt: str, context: list[Doc]) -> LLMRequest: ...


class Retriever(Protocol):
    def retrieve(self, prompt: str) -> list[Doc]: ...


class LLMProvider(Protocol):
    def generate(self, req: LLMRequest) -> str: ...


class Pipeline(Protocol):
    def run(self, prompt: str) -> AmbienceContent: ...
```

- [ ] **Step 3: Run mypy on both files**

```bash
cd backend && uv run mypy app/models/errors.py app/rag/interfaces.py
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/errors.py backend/app/rag/interfaces.py
git commit -m "feat: add domain exceptions and RAG interface protocols"
```

---

## Task 4: Mock RAG components + conformance tests

**Files:**
- Create: `backend/app/rag/providers/mock.py`
- Create: `backend/tests/rag/providers/test_mock.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/rag/providers/test_mock.py`:
```python
import json

from app.models.ambience import AmbienceContent
from app.rag.interfaces import Doc, LLMRequest
from app.rag.providers.mock import MockPromptBuilder, MockProvider, NoOpRetriever


def test_no_op_retriever_returns_empty():
    r = NoOpRetriever()
    result = r.retrieve("any prompt")
    assert result == []


def test_mock_prompt_builder_returns_llm_request():
    b = MockPromptBuilder()
    req = b.build("rainy jazz", [])
    assert isinstance(req, LLMRequest)
    assert "rainy jazz" in req.user


def test_mock_prompt_builder_ignores_context():
    b = MockPromptBuilder()
    req_no_ctx = b.build("test", [])
    req_with_ctx = b.build("test", [Doc(content="extra context")])
    assert req_no_ctx.user == req_with_ctx.user


def test_mock_provider_returns_valid_json():
    p = MockProvider()
    raw = p.generate(LLMRequest(system="", user="test"))
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_mock_provider_output_validates_as_ambience_content():
    p = MockProvider()
    raw = p.generate(LLMRequest(system="", user="test"))
    content = AmbienceContent.model_validate_json(raw)
    assert len(content.name) > 0
    assert len(content.filters) >= 1


def test_mock_provider_is_deterministic():
    p = MockProvider()
    req = LLMRequest(system="", user="anything")
    assert p.generate(req) == p.generate(req)
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend && uv run pytest tests/rag/providers/test_mock.py -v
```

Expected: `ImportError` (module does not exist yet).

- [ ] **Step 3: Implement `backend/app/rag/providers/mock.py`**

```python
from __future__ import annotations

import json

from app.rag.interfaces import Doc, LLMRequest


class NoOpRetriever:
    def retrieve(self, prompt: str) -> list[Doc]:
        return []


class MockPromptBuilder:
    def build(self, prompt: str, context: list[Doc]) -> LLMRequest:
        return LLMRequest(system="You are a music ambience generator.", user=prompt)


_MOCK_RESPONSE: dict[str, object] = {
    "name": "Canned Mock Ambience",
    "intension": "A deterministic mock ambience for skeleton testing.",
    "publico": "Developers verifying the end-to-end skeleton.",
    "shuffle_rule": False,
    "filters": [
        {
            "shuffle_rule": True,
            "genres": ["488"],
            "moods": ["Cool", "Lively"],
            "album_release_dates": ["2010s"],
            "artist_origin_regions": [],
            "artist_origin_countries": [],
            "explicit": False,
            "tracks_exceptions": [],
            "popularity": {"min": 35, "max": None},
            "acousticness": {"min": None, "max": None},
            "danceability": {"min": None, "max": None},
            "energy": {"min": 40, "max": 80},
            "instrumentalness": {"min": None, "max": None},
            "liveness": {"min": None, "max": None},
            "loudness": {"min": None, "max": None},
            "speechiness": {"min": None, "max": None},
            "tempo": {"min": 110, "max": None},
            "valence": {"min": None, "max": None},
        }
    ],
}


class MockProvider:
    def generate(self, req: LLMRequest) -> str:
        return json.dumps(_MOCK_RESPONSE)
```

- [ ] **Step 4: Run tests — expect green**

```bash
cd backend && uv run pytest tests/rag/providers/test_mock.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run ruff and mypy**

```bash
cd backend && uv run ruff check app/rag/providers/mock.py && uv run mypy app/rag/providers/mock.py
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/rag/providers/mock.py backend/tests/rag/providers/test_mock.py
git commit -m "feat: add mock RAG components (provider, builder, retriever)"
```

---

## Task 5: AmbiencePipeline + tests

**Files:**
- Create: `backend/app/rag/pipeline.py`
- Create: `backend/tests/rag/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/rag/test_pipeline.py`:
```python
import json

import pytest

from app.models.ambience import AmbienceContent, Filter
from app.models.errors import AmbienceGenerationError
from app.rag.interfaces import Doc, LLMRequest
from app.rag.pipeline import AmbiencePipeline


class _FakeProvider:
    def __init__(self, raw: str) -> None:
        self._raw = raw

    def generate(self, req: LLMRequest) -> str:
        return self._raw


class _FakeBuilder:
    def build(self, prompt: str, context: list[Doc]) -> LLMRequest:
        return LLMRequest(system="", user=prompt)


class _FakeRetriever:
    def retrieve(self, prompt: str) -> list[Doc]:
        return [Doc(content="context")]


_VALID_CONTENT = json.dumps(
    {
        "name": "Test",
        "intension": "i",
        "publico": "p",
        "shuffle_rule": False,
        "filters": [{}],
    }
)


def _make_pipeline(raw: str) -> AmbiencePipeline:
    return AmbiencePipeline(
        provider=_FakeProvider(raw),
        retriever=_FakeRetriever(),
        builder=_FakeBuilder(),
    )


def test_run_returns_ambience_content():
    pipeline = _make_pipeline(_VALID_CONTENT)
    result = pipeline.run("some prompt")
    assert isinstance(result, AmbienceContent)
    assert result.name == "Test"


def test_run_passes_prompt_to_builder():
    received: list[str] = []

    class _CapturingBuilder:
        def build(self, prompt: str, context: list[Doc]) -> LLMRequest:
            received.append(prompt)
            return LLMRequest(system="", user=prompt)

    pipeline = AmbiencePipeline(
        provider=_FakeProvider(_VALID_CONTENT),
        retriever=_FakeRetriever(),
        builder=_CapturingBuilder(),
    )
    pipeline.run("hello world")
    assert received == ["hello world"]


def test_invalid_json_raises_generation_error():
    pipeline = _make_pipeline("not json at all")
    with pytest.raises(AmbienceGenerationError):
        pipeline.run("prompt")


def test_invalid_schema_raises_generation_error():
    bad = json.dumps({"name": "", "intension": "i", "publico": "p", "filters": []})
    pipeline = _make_pipeline(bad)
    with pytest.raises(AmbienceGenerationError):
        pipeline.run("prompt")
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend && uv run pytest tests/rag/test_pipeline.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `backend/app/rag/pipeline.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect green**

```bash
cd backend && uv run pytest tests/rag/test_pipeline.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run ruff and mypy**

```bash
cd backend && uv run ruff check app/rag/pipeline.py && uv run mypy app/rag/pipeline.py
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/rag/pipeline.py backend/tests/rag/test_pipeline.py
git commit -m "feat: add AmbiencePipeline (compose + validate LLM output)"
```

---

## Task 6: AmbienceStore Protocol + LocalStore + tests

**Files:**
- Create: `backend/app/persistence/interfaces.py`
- Create: `backend/app/persistence/local_store.py`
- Create: `backend/tests/persistence/test_local_store.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/persistence/test_local_store.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.ambience import Ambience, Filter
from app.models.errors import AmbienceStorageError
from app.persistence.local_store import LocalStore


def _make_ambience(uuid: str = "test-uuid") -> Ambience:
    return Ambience(
        uuid=uuid,
        user_id="u1",
        prompt="rainy afternoon jazz",
        fingerprint="fp1",
        created_at=datetime(2026, 6, 9, tzinfo=timezone.utc),
        name="Jazz",
        intension="Relaxed",
        publico="Everyone",
        shuffle_rule=False,
        filters=[Filter(genres=["488"], moods=["Cool"])],
    )


def test_save_writes_json_file(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    a = _make_ambience()
    store.save(a)
    expected_path = tmp_path / f"{a.uuid}.json"
    assert expected_path.exists()


def test_save_content_round_trips(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    a = _make_ambience()
    store.save(a)
    raw = (tmp_path / f"{a.uuid}.json").read_text()
    data = json.loads(raw)
    assert data["uuid"] == a.uuid
    assert data["fingerprint"] == a.fingerprint
    assert data["filters"][0]["genres"] == ["488"]


def test_save_creates_data_dir_if_missing(tmp_path: Path) -> None:
    new_dir = tmp_path / "subdir" / "data"
    store = LocalStore(data_dir=new_dir)
    store.save(_make_ambience())
    assert new_dir.exists()


def test_save_uses_uuid_as_filename(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    store.save(_make_ambience("my-unique-id"))
    assert (tmp_path / "my-unique-id.json").exists()


def test_save_raises_storage_error_on_write_failure(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    a = _make_ambience()
    with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        with pytest.raises(AmbienceStorageError):
            store.save(a)
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend && uv run pytest tests/persistence/test_local_store.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `backend/app/persistence/interfaces.py`**

```python
from typing import Protocol

from app.models.ambience import Ambience


class AmbienceStore(Protocol):
    def save(self, ambience: Ambience) -> None: ...
```

- [ ] **Step 4: Write `backend/app/persistence/local_store.py`**

```python
from __future__ import annotations

from pathlib import Path

from app.models.ambience import Ambience
from app.models.errors import AmbienceStorageError


class LocalStore:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, ambience: Ambience) -> None:
        path = self._data_dir / f"{ambience.uuid}.json"
        try:
            path.write_text(ambience.model_dump_json(indent=2))
        except OSError as exc:
            raise AmbienceStorageError(f"Failed to write ambience: {exc}") from exc
```

- [ ] **Step 5: Run tests — expect green**

```bash
cd backend && uv run pytest tests/persistence/test_local_store.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Run ruff and mypy**

```bash
cd backend && uv run ruff check app/persistence/ && uv run mypy app/persistence/
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/persistence/ backend/tests/persistence/
git commit -m "feat: add AmbienceStore protocol and LocalStore implementation"
```

---

## Task 7: RateLimiter Protocol + InMemoryRateLimiter + tests

**Files:**
- Create: `backend/app/ratelimit/interfaces.py`
- Create: `backend/app/ratelimit/in_memory.py`
- Create: `backend/tests/ratelimit/test_in_memory.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/ratelimit/test_in_memory.py`:
```python
import pytest

from app.models.errors import RateLimitExceeded
from app.ratelimit.in_memory import InMemoryRateLimiter


def test_allows_requests_under_limit() -> None:
    limiter = InMemoryRateLimiter(limit=3, window_seconds=60)
    limiter.check("u1")
    limiter.check("u1")
    limiter.check("u1")  # 3rd — still allowed


def test_blocks_on_limit_exceeded() -> None:
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    limiter.check("u1")
    limiter.check("u1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("u1")


def test_rate_limit_exceeded_carries_retry_after() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=30)
    limiter.check("u1")
    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter.check("u1")
    assert exc_info.value.retry_after == 30


def test_different_users_are_independent() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    limiter.check("u1")
    limiter.check("u2")  # different user — should not raise


def test_expired_calls_do_not_count() -> None:
    import time
    limiter = InMemoryRateLimiter(limit=1, window_seconds=1)
    limiter.check("u1")
    time.sleep(1.1)
    limiter.check("u1")  # old call expired — should not raise
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend && uv run pytest tests/ratelimit/test_in_memory.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `backend/app/ratelimit/interfaces.py`**

```python
from typing import Protocol


class RateLimiter(Protocol):
    def check(self, user_id: str) -> None: ...
```

- [ ] **Step 4: Write `backend/app/ratelimit/in_memory.py`**

```python
from __future__ import annotations

import time
from collections import defaultdict

from app.models.errors import RateLimitExceeded


class InMemoryRateLimiter:
    """Fixed-window rate limiter keyed by user_id.

    Not suitable for multi-process or multi-instance deployments — use a
    Redis-backed implementation in production.
    """

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._log: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> None:
        now = time.monotonic()
        cutoff = now - self._window
        calls = [t for t in self._log[user_id] if t > cutoff]
        if len(calls) >= self._limit:
            raise RateLimitExceeded(retry_after=self._window)
        calls.append(now)
        self._log[user_id] = calls
```

- [ ] **Step 5: Run tests — expect green**

```bash
cd backend && uv run pytest tests/ratelimit/test_in_memory.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Run ruff and mypy**

```bash
cd backend && uv run ruff check app/ratelimit/ && uv run mypy app/ratelimit/
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/ratelimit/ backend/tests/ratelimit/
git commit -m "feat: add RateLimiter protocol and InMemoryRateLimiter"
```

---

## Task 8: AmbienceService + tests

**Files:**
- Create: `backend/app/services/ambience_service.py`
- Create: `backend/tests/services/test_ambience_service.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/services/test_ambience_service.py`:
```python
from app.models.ambience import Ambience, AmbienceContent, AmbienceRequest, Filter
from app.models.errors import AmbienceGenerationError, AmbienceStorageError
from app.services.ambience_service import AmbienceService
import pytest


class _FakePipeline:
    def __init__(self, content: AmbienceContent) -> None:
        self._content = content

    def run(self, prompt: str) -> AmbienceContent:
        return self._content


class _RaisingPipeline:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def run(self, prompt: str) -> AmbienceContent:
        raise self._exc


class _FakeStore:
    def __init__(self) -> None:
        self.saved: list[Ambience] = []

    def save(self, ambience: Ambience) -> None:
        self.saved.append(ambience)


class _FailingStore:
    def save(self, ambience: Ambience) -> None:
        raise AmbienceStorageError("disk full")


def _make_content() -> AmbienceContent:
    return AmbienceContent(
        name="Test",
        intension="i",
        publico="p",
        shuffle_rule=False,
        filters=[Filter(genres=["488"])],
    )


def _make_request(prompt: str = "rainy jazz", user_id: str = "u1") -> AmbienceRequest:
    return AmbienceRequest(prompt=prompt, user_id=user_id)


def test_create_returns_ambience() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    result = svc.create(_make_request())
    assert isinstance(result, Ambience)
    assert result.name == "Test"


def test_create_persists_ambience() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    svc.create(_make_request())
    assert len(store.saved) == 1


def test_create_sets_user_id_and_prompt() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    result = svc.create(_make_request(prompt="rainy jazz", user_id="u42"))
    assert result.user_id == "u42"
    assert result.prompt == "rainy jazz"


def test_create_generates_unique_uuids() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request())
    r2 = svc.create(_make_request())
    assert r1.uuid != r2.uuid


def test_fingerprint_is_deterministic() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request(prompt="rainy jazz", user_id="u1"))
    r2 = svc.create(_make_request(prompt="rainy jazz", user_id="u1"))
    assert r1.fingerprint == r2.fingerprint


def test_fingerprint_differs_for_different_users() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request(user_id="u1"))
    r2 = svc.create(_make_request(user_id="u2"))
    assert r1.fingerprint != r2.fingerprint


def test_fingerprint_normalizes_prompt_whitespace() -> None:
    store = _FakeStore()
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=store)
    r1 = svc.create(_make_request(prompt="rainy  jazz"))
    r2 = svc.create(_make_request(prompt="rainy jazz"))
    assert r1.fingerprint == r2.fingerprint


def test_generation_error_propagates() -> None:
    svc = AmbienceService(
        pipeline=_RaisingPipeline(AmbienceGenerationError("bad")),
        store=_FakeStore(),
    )
    with pytest.raises(AmbienceGenerationError):
        svc.create(_make_request())


def test_storage_error_propagates() -> None:
    svc = AmbienceService(pipeline=_FakePipeline(_make_content()), store=_FailingStore())
    with pytest.raises(AmbienceStorageError):
        svc.create(_make_request())
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend && uv run pytest tests/services/test_ambience_service.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `backend/app/services/ambience_service.py`**

```python
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from app.models.ambience import Ambience, AmbienceRequest
from app.persistence.interfaces import AmbienceStore
from app.rag.interfaces import Pipeline


class AmbienceService:
    def __init__(self, pipeline: Pipeline, store: AmbienceStore) -> None:
        self._pipeline = pipeline
        self._store = store

    def create(self, request: AmbienceRequest) -> Ambience:
        content = self._pipeline.run(request.prompt)
        ambience = Ambience(
            uuid=str(uuid.uuid4()),
            user_id=request.user_id,
            prompt=request.prompt,
            fingerprint=self._fingerprint(request.user_id, request.prompt),
            created_at=datetime.now(timezone.utc),
            name=content.name,
            intension=content.intension,
            publico=content.publico,
            shuffle_rule=content.shuffle_rule,
            filters=content.filters,
        )
        self._store.save(ambience)
        return ambience

    @staticmethod
    def _fingerprint(user_id: str, prompt: str) -> str:
        normalized = " ".join(prompt.strip().lower().split())
        payload = f"{user_id}:{normalized}".encode()
        return hashlib.sha256(payload).hexdigest()
```

- [ ] **Step 4: Run tests — expect green**

```bash
cd backend && uv run pytest tests/services/test_ambience_service.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Run ruff and mypy**

```bash
cd backend && uv run ruff check app/services/ && uv run mypy app/services/
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ambience_service.py backend/tests/services/test_ambience_service.py
git commit -m "feat: add AmbienceService (orchestrate pipeline, store, fingerprint)"
```

---

## Task 9: Config + app factory + API router + controller tests

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/ambiences.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/api/test_ambiences.py`
- Create: `backend/tests/conftest.py`

This is the largest task — it wires everything together. Write controller tests first.

- [ ] **Step 1: Write `backend/tests/conftest.py`**

```python
from datetime import datetime, timezone

import pytest

from app.models.ambience import Ambience, AmbienceContent, AmbienceRequest, Filter, Range


@pytest.fixture
def sample_filter() -> Filter:
    return Filter(
        shuffle_rule=True,
        genres=["488"],
        moods=["Cool", "Lively"],
        energy=Range(min=40, max=80),
        tempo=Range(min=110, max=None),
        popularity=Range(min=35, max=None),
    )


@pytest.fixture
def sample_ambience(sample_filter: Filter) -> Ambience:
    return Ambience(
        uuid="test-uuid-1234",
        user_id="user-1",
        prompt="rainy afternoon jazz",
        fingerprint="abc123fingerprint",
        created_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc),
        name="Rainy Afternoon Jazz",
        intension="A relaxed rainy-day atmosphere",
        publico="Remote workers and creatives",
        shuffle_rule=False,
        filters=[sample_filter],
    )
```

- [ ] **Step 2: Write the failing controller tests**

`backend/tests/api/test_ambiences.py`:
```python
import pytest
from fastapi.testclient import TestClient

from app.models.ambience import Ambience, AmbienceRequest
from app.models.errors import (
    AmbienceGenerationError,
    AmbienceStorageError,
    LLMRateLimitError,
    RateLimitExceeded,
)


class _FakeService:
    def __init__(self, result: Ambience) -> None:
        self._result = result

    def create(self, request: AmbienceRequest) -> Ambience:
        return self._result


class _RaisingService:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def create(self, request: AmbienceRequest) -> Ambience:
        raise self._exc


class _PassLimiter:
    def check(self, user_id: str) -> None:
        pass


class _BlockLimiter:
    def check(self, user_id: str) -> None:
        raise RateLimitExceeded(retry_after=30)


def _make_client(service: object, limiter: object) -> TestClient:
    from app.main import create_app
    app = create_app(service=service, rate_limiter=limiter)  # type: ignore[arg-type]
    return TestClient(app, raise_server_exceptions=False)


def test_create_returns_201(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 201


def test_create_returns_location_header(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.headers["location"] == f"/ambiences/{sample_ambience.uuid}"


def test_create_response_contains_uuid(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.json()["uuid"] == sample_ambience.uuid


def test_create_response_contains_fingerprint(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert "fingerprint" in res.json()


def test_missing_prompt_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"user_id": "u1"})
    assert res.status_code == 422


def test_missing_user_id_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz"})
    assert res.status_code == 422


def test_prompt_too_short_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "ab", "user_id": "u1"})
    assert res.status_code == 422


def test_prompt_too_long_returns_422(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "x" * 2001, "user_id": "u1"})
    assert res.status_code == 422


def test_rate_limit_returns_429(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _BlockLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 429


def test_rate_limit_includes_retry_after_header(sample_ambience: Ambience) -> None:
    client = _make_client(_FakeService(sample_ambience), _BlockLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.headers.get("retry-after") == "30"


def test_generation_error_returns_502(sample_ambience: Ambience) -> None:
    client = _make_client(_RaisingService(AmbienceGenerationError("fail")), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 502


def test_llm_rate_limit_returns_503(sample_ambience: Ambience) -> None:
    client = _make_client(_RaisingService(LLMRateLimitError(retry_after=60)), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 503


def test_llm_rate_limit_includes_retry_after(sample_ambience: Ambience) -> None:
    client = _make_client(_RaisingService(LLMRateLimitError(retry_after=60)), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.headers.get("retry-after") == "60"


def test_storage_error_returns_503(sample_ambience: Ambience) -> None:
    client = _make_client(_RaisingService(AmbienceStorageError("full")), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert res.status_code == 503


def test_error_response_does_not_leak_internals(sample_ambience: Ambience) -> None:
    client = _make_client(_RaisingService(AmbienceGenerationError("secret trace")), _PassLimiter())
    res = client.post("/ambiences", json={"prompt": "rainy jazz", "user_id": "u1"})
    assert "secret trace" not in res.text
```

- [ ] **Step 3: Run tests — expect failures**

```bash
cd backend && uv run pytest tests/api/test_ambiences.py -v
```

Expected: `ImportError` (main and api don't exist yet).

- [ ] **Step 4: Write `backend/app/core/config.py`**

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: str = "mock"
    storage: str = "local"
    data_dir: Path = Path("./backend/data")
    cors_allow_origins: list[str] = ["http://localhost:5500"]
    rate_limit_per_minute: int = 10


settings = Settings()
```

- [ ] **Step 5: Write `backend/app/api/ambiences.py`**

```python
from fastapi import APIRouter, Request, Response

from app.models.ambience import Ambience, AmbienceRequest

router = APIRouter(prefix="/ambiences", tags=["ambiences"])


@router.post("", status_code=201, response_model=Ambience)
async def create_ambience(
    body: AmbienceRequest,
    request: Request,
    response: Response,
) -> Ambience:
    request.app.state.rate_limiter.check(body.user_id)
    ambience: Ambience = request.app.state.service.create(body)
    response.headers["Location"] = f"/ambiences/{ambience.uuid}"
    return ambience
```

- [ ] **Step 6: Write `backend/app/main.py`**

```python
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.ambiences import router as ambiences_router
from app.core.config import settings
from app.models.errors import (
    AmbienceGenerationError,
    AmbienceStorageError,
    LLMRateLimitError,
    RateLimitExceeded,
)


def _build_default_service() -> Any:
    from app.persistence.local_store import LocalStore
    from app.rag.pipeline import AmbiencePipeline
    from app.rag.providers.mock import MockPromptBuilder, MockProvider, NoOpRetriever
    from app.services.ambience_service import AmbienceService

    pipeline = AmbiencePipeline(
        provider=MockProvider(),
        retriever=NoOpRetriever(),
        builder=MockPromptBuilder(),
    )
    store = LocalStore(data_dir=settings.data_dir)
    return AmbienceService(pipeline=pipeline, store=store)


def _build_default_limiter() -> Any:
    from app.ratelimit.in_memory import InMemoryRateLimiter

    return InMemoryRateLimiter(limit=settings.rate_limit_per_minute)


def create_app(
    *,
    service: Any = None,
    rate_limiter: Any = None,
) -> FastAPI:
    app = FastAPI(title="Ambience API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["POST"],
        allow_headers=["*"],
    )

    app.state.service = service or _build_default_service()
    app.state.rate_limiter = rate_limiter or _build_default_limiter()

    app.include_router(ambiences_router)

    @app.exception_handler(RateLimitExceeded)
    async def _on_rate_limit(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(AmbienceGenerationError)
    async def _on_generation_error(
        request: Request, exc: AmbienceGenerationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": "Ambience generation failed. Please try again."},
        )

    @app.exception_handler(LLMRateLimitError)
    async def _on_llm_rate_limit(
        request: Request, exc: LLMRateLimitError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Generation service is busy. Please try again later."},
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(AmbienceStorageError)
    async def _on_storage_error(
        request: Request, exc: AmbienceStorageError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Storage unavailable. Please try again later."},
        )

    return app


app = create_app()
```

- [ ] **Step 7: Run controller tests — expect green**

```bash
cd backend && uv run pytest tests/api/test_ambiences.py -v
```

Expected: all 15 tests PASS.

- [ ] **Step 8: Run the full test suite**

```bash
cd backend && uv run pytest -v
```

Expected: all tests PASS (models + rag + persistence + ratelimit + services + api).

- [ ] **Step 9: Run ruff and mypy across the whole app**

```bash
cd backend && uv run ruff check app/ && uv run mypy app/
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
git add backend/app/core/ backend/app/api/ backend/app/main.py \
  backend/tests/conftest.py backend/tests/api/
git commit -m "feat: add config, API router, app factory, and controller tests"
```

---

## Task 10: Generate and commit `openapi.yaml`

**Files:**
- Create: `backend/openapi.yaml`

- [ ] **Step 1: Start the app and export the schema**

```bash
cd backend && uv run python -c "
import yaml
from app.main import app

schema = app.openapi()
with open('openapi.yaml', 'w') as f:
    yaml.dump(schema, f, sort_keys=False, allow_unicode=True)
print('openapi.yaml written')
"
```

Expected: `openapi.yaml written` and `backend/openapi.yaml` is created.

- [ ] **Step 2: Verify the schema contains the ambiences endpoint**

```bash
grep -A5 "\/ambiences" backend/openapi.yaml
```

Expected: output shows the `post` operation under `/ambiences`.

- [ ] **Step 3: Commit**

```bash
git add backend/openapi.yaml
git commit -m "chore: generate openapi.yaml from FastAPI routes"
```

---

## Task 11: Frontend (index.html, styles.css, app.js)

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/styles.css`
- Create: `frontend/app.js`

No automated tests for the frontend — verified by running manually in Task 12 (docker-compose).

- [ ] **Step 1: Write `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ambience Generator</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main>
    <h1>Ambience Generator</h1>

    <section class="prompt-section">
      <label for="prompt">Describe your ambience</label>
      <p class="hint">
        Describe the vibe, intention, and audience. For example:
        <em>"High-energy workout music for gym-goers who love modern hip-hop and want to feel motivated."</em>
      </p>
      <textarea
        id="prompt"
        placeholder="Describe the feeling, intention, and target audience…"
        maxlength="2000"
        rows="4"
      ></textarea>
      <div class="char-counter"><span id="char-count">0</span> / 2000</div>
      <input id="user-id" type="text" placeholder="User ID" required>
      <button id="submit-btn" type="button">Generate Ambience</button>
    </section>

    <div id="error-region" class="error hidden" role="alert"></div>
    <section id="result-panel" class="result hidden" aria-live="polite"></section>
  </main>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `frontend/styles.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #f5f5f5;
  color: #1a1a1a;
  min-height: 100vh;
  line-height: 1.5;
}

main {
  max-width: 860px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

h1 { font-size: 1.75rem; margin-bottom: 1.5rem; }
h2 { font-size: 1.25rem; }
h3 { font-size: .95rem; color: #555; margin: .75rem 0 .4rem; font-weight: 600; }

/* Prompt form */
.prompt-section {
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  display: flex;
  flex-direction: column;
  gap: .75rem;
}
label { font-weight: 600; }
.hint { font-size: .875rem; color: #666; }
.hint em { font-style: normal; color: #444; }

textarea {
  width: 100%;
  padding: .75rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
}
textarea:focus { outline: 2px solid #1a1a1a; border-color: transparent; }

.char-counter { font-size: .8rem; color: #888; text-align: right; }

input[type="text"] {
  width: 100%;
  padding: .6rem .75rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 1rem;
  font-family: inherit;
}

button {
  padding: .75rem 1.5rem;
  background: #1a1a1a;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  align-self: flex-start;
  transition: background .15s;
}
button:hover:not(:disabled) { background: #333; }
button:disabled { background: #888; cursor: default; }

/* Error */
.error {
  margin-top: 1rem;
  padding: .75rem 1rem;
  background: #fff0f0;
  border: 1px solid #fcc;
  border-radius: 6px;
  color: #c00;
}

.hidden { display: none; }

/* Result card */
.result {
  margin-top: 1.5rem;
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}

.ambience-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: .75rem;
  flex-wrap: wrap;
}

.field { margin: .4rem 0; }

/* Badges */
.badge {
  font-size: .75rem;
  font-weight: 700;
  padding: .25rem .65rem;
  border-radius: 999px;
  background: #e5e5e5;
  color: #555;
  white-space: nowrap;
}
.badge.on { background: #d1fae5; color: #065f46; }
.badge.warn { background: #fef3c7; color: #92400e; }

/* Filters */
.filter {
  margin-top: 1.25rem;
  padding: 1rem;
  border: 1px solid #ececec;
  border-radius: 6px;
}

/* Chips */
.chip-group { margin: .35rem 0; font-size: .875rem; }
.chip {
  display: inline-block;
  background: #f0f0f0;
  border-radius: 999px;
  padding: .2rem .65rem;
  margin: .15rem .1rem;
  font-size: .8rem;
}

/* Audio feature ranges */
.ranges { margin-top: .5rem; font-size: .85rem; color: #555; }

/* Metadata + raw JSON */
details { margin-top: 1rem; }
summary { cursor: pointer; font-size: .875rem; color: #888; user-select: none; }
details[open] summary { margin-bottom: .5rem; }
.meta p { font-size: .8rem; color: #888; margin: .2rem 0; font-family: monospace; }
pre {
  padding: .75rem;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: .78rem;
  overflow: auto;
  max-height: 400px;
}
```

- [ ] **Step 3: Write `frontend/app.js`**

```javascript
const API_BASE = "http://localhost:8000";

const promptEl  = document.getElementById("prompt");
const charCount = document.getElementById("char-count");
const submitBtn = document.getElementById("submit-btn");
const userIdEl  = document.getElementById("user-id");
const errorDiv  = document.getElementById("error-region");
const resultEl  = document.getElementById("result-panel");

promptEl.addEventListener("input", () => {
  charCount.textContent = promptEl.value.length;
});

submitBtn.addEventListener("click", async () => {
  const prompt  = promptEl.value.trim();
  const user_id = userIdEl.value.trim();
  if (!prompt || !user_id) return;

  setLoading(true);
  clearError();
  resultEl.classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/ambiences`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, user_id }),
    });

    if (!res.ok) { await handleError(res); return; }

    const ambience = await res.json();
    renderAmbience(ambience);
  } catch {
    showError("Network error. Is the backend running?");
  } finally {
    setLoading(false);
  }
});

async function handleError(res) {
  const retryAfter = res.headers.get("Retry-After") || "60";
  if (res.status === 429) {
    showError(`Too many requests. Try again in ${retryAfter}s.`);
  } else if (res.status === 422) {
    showError("Check your prompt — must be 3 to 2000 characters, and User ID is required.");
  } else {
    showError("Generation service is busy. Please try again in a moment.");
  }
}

function setLoading(on) {
  submitBtn.disabled = on;
  submitBtn.textContent = on ? "Generating…" : "Generate Ambience";
}

function clearError() {
  errorDiv.classList.add("hidden");
  errorDiv.textContent = "";
}

function showError(msg) {
  errorDiv.textContent = msg;
  errorDiv.classList.remove("hidden");
}

// ── Rendering ──────────────────────────────────────────────────────────────

function renderAmbience(a) {
  const shuffleBadge = badge(a.shuffle_rule ? "Shuffle ON" : "Shuffle OFF", a.shuffle_rule ? "on" : "");
  let html = `
    <div class="ambience-header">
      <h2>${esc(a.name)}</h2>
      ${shuffleBadge}
    </div>
    <p class="field"><strong>Intension:</strong> ${esc(a.intension)}</p>
    <p class="field"><strong>Público:</strong> ${esc(a.publico)}</p>
  `;

  a.filters.forEach((f, i) => {
    html += `<div class="filter"><h3>Filter ${i + 1}</h3>`;
    html += badge(f.shuffle_rule ? "Shuffle ON" : "Shuffle OFF", f.shuffle_rule ? "on" : "");
    html += badge(f.explicit ? "Explicit YES" : "Explicit NO", f.explicit ? "warn" : "");

    if (f.genres?.length)               html += chips("Genres", f.genres);
    if (f.moods?.length)                html += chips("Moods", f.moods);
    if (f.album_release_dates?.length)  html += chips("Decades", f.album_release_dates);
    if (f.artist_origin_regions?.length)   html += chips("Regions", f.artist_origin_regions);
    if (f.artist_origin_countries?.length) html += chips("Countries", f.artist_origin_countries);

    const FEATURES = [
      "popularity","energy","danceability","valence","tempo",
      "acousticness","instrumentalness","liveness","loudness","speechiness",
    ];
    const rangeLabels = FEATURES.map(k => rangeLabel(k, f[k])).filter(Boolean);
    if (rangeLabels.length) {
      html += `<p class="ranges">${rangeLabels.join(" &nbsp;·&nbsp; ")}</p>`;
    }
    html += "</div>";
  });

  html += `
    <details class="meta">
      <summary>Metadata</summary>
      <p>uuid: ${esc(a.uuid)}</p>
      <p>fingerprint: ${esc(a.fingerprint)}</p>
      <p>created: ${esc(a.created_at)}</p>
    </details>
    <details class="raw">
      <summary>Raw JSON</summary>
      <pre>${esc(JSON.stringify(a, null, 2))}</pre>
    </details>
  `;

  resultEl.innerHTML = html;
  resultEl.classList.remove("hidden");
}

function badge(text, cls = "") {
  return `<span class="badge${cls ? " " + cls : ""}">${esc(text)}</span>`;
}

function chips(label, items) {
  const chipHtml = items.map(i => `<span class="chip">${esc(i)}</span>`).join("");
  return `<div class="chip-group"><strong>${esc(label)}:</strong> ${chipHtml}</div>`;
}

function rangeLabel(key, r) {
  if (!r || (r.min == null && r.max == null)) return "";
  const label = key.charAt(0).toUpperCase() + key.slice(1);
  if (r.min != null && r.max != null) return `${label}&nbsp;${r.min}–${r.max}`;
  if (r.min != null) return `${label}&nbsp;≥${r.min}`;
  return `${label}&nbsp;≤${r.max}`;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add vanilla frontend (prompt input, ambience render)"
```

---

## Task 12: Docker

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen
COPY app ./app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./backend/data:/app/backend/data

  frontend:
    image: nginx:alpine
    ports:
      - "5500:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
```

- [ ] **Step 3: Build and start the stack**

```bash
docker compose up --build
```

Expected: backend starts on `http://localhost:8000`; frontend on `http://localhost:5500`.

- [ ] **Step 4: Smoke test the API**

```bash
curl -s -X POST http://localhost:8000/ambiences \
  -H "Content-Type: application/json" \
  -d '{"prompt": "rainy afternoon jazz for remote workers", "user_id": "u1"}' \
  | python3 -m json.tool | head -20
```

Expected: JSON response with `uuid`, `fingerprint`, `name`, `filters`.

- [ ] **Step 5: Verify the frontend**

Open `http://localhost:5500` in a browser. Type a prompt, enter a User ID, click "Generate Ambience". Result panel should show the ambience with chips, range labels, and a "Raw JSON" toggle.

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose for backend + frontend"
```

---

## Final verification

- [ ] **Run the full test suite one last time**

```bash
cd backend && uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Ruff + mypy clean pass**

```bash
cd backend && uv run ruff check app/ tests/ && uv run mypy app/
```

Expected: no errors.

- [ ] **Confirm openapi.yaml is committed and matches current routes**

```bash
grep "post:" backend/openapi.yaml
```

Expected: one `post:` entry under `/ambiences`.
