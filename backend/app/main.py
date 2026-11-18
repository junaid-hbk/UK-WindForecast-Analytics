"""FastAPI application factory.

Run locally with::

    uvicorn app.main:app --reload --port 8000

OpenAPI documentation is served at ``/docs`` and ``/openapi.json``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

DESCRIPTION = """
WindPulse UK — renewable forecast and procurement intelligence for national GB wind.

Data provenance: Elexon BMRS Insights API — `FUELHH` (actual half-hourly wind outturn,
`fuelType=WIND`) and `WINDFOR` (hourly national wind forecast, every publication vintage
preserved).

Method: each delivery interval is paired with the **latest forecast vintage published at or
before the configured day-ahead decision cutoff**. Forecasts published after the cutoff are
never used. Accuracy metrics exclude missing observations and report them; no missing value is
ever replaced by zero.

The procurement endpoint is an **illustrative arithmetic estimate**, not a purchasing
recommendation.
""".strip()

TAGS_METADATA = [
    {"name": "health", "description": "Liveness and readiness."},
    {"name": "meta", "description": "Cutoff policies, method flags, metric definitions."},
    {"name": "actual generation", "description": "FUELHH WIND outturn."},
    {"name": "forecast", "description": "As-of selection, vintage lineage, raw vintages."},
    {"name": "forecast accuracy", "description": "MAE, RMSE, WAPE, bias, lead time."},
    {"name": "procurement", "description": "Illustrative demand-scenario delta."},
    {"name": "data status", "description": "Coverage, freshness, runs, data-quality issues."},
    {"name": "administration", "description": "Token-guarded ingestion and rebuild."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Accepts explicit settings for tests."""
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application_startup",
            extra={
                "app": resolved.app_name,
                "version": resolved.app_version,
                "environment": resolved.environment,
                "admin_enabled": resolved.admin_enabled,
            },
        )
        yield
        logger.info("application_shutdown")

    app = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        description=DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Token"],
        max_age=600,
    )

    # Make the settings this factory was given authoritative for every
    # dependency too. Without this, routes would resolve the cached
    # ``get_settings()`` singleton, so an app built with explicit settings (as
    # tests and embedded deployments do) would silently use the environment's
    # values for CORS, admin token, page limits and the database URL.
    app.dependency_overrides[get_settings] = lambda: resolved

    register_exception_handlers(app)
    app.include_router(api_router, prefix=resolved.api_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": resolved.app_name,
            "version": resolved.app_version,
            "docs": "/docs",
            "api": resolved.api_prefix,
        }

    return app


app = create_app()
