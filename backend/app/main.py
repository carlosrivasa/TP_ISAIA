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
from app.persistence.interfaces import AmbienceStore
from app.rag.interfaces import Pipeline
from app.services.ambience_service import AmbienceService


def _build_pipeline() -> Pipeline:
    if settings.llm_provider == "mock":
        from app.rag.pipeline import AmbiencePipeline
        from app.rag.providers.mock import (
            MockPromptBuilder,
            MockProvider,
            NoOpRetriever,
        )

        return AmbiencePipeline(
            provider=MockProvider(),
            retriever=NoOpRetriever(),
            builder=MockPromptBuilder(),
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")


def _build_store() -> AmbienceStore:
    if settings.storage == "local":
        from app.persistence.local_store import LocalStore

        return LocalStore(data_dir=settings.data_dir)
    raise ValueError(f"Unknown STORAGE: {settings.storage!r}")


def _build_default_service() -> AmbienceService:
    return AmbienceService(pipeline=_build_pipeline(), store=_build_store())


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
        allow_headers=["Content-Type"],
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
