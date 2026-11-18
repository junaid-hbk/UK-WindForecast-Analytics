"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import SessionDep, SettingsDep
from app.core.errors import AppError
from app.schemas.common import HealthOut, ReadinessOut

router = APIRouter(tags=["health"])


class NotReadyError(AppError):
    """The service is running but cannot serve data."""

    code = "NOT_READY"
    status_code = 503


@router.get("/health", response_model=HealthOut, summary="Liveness check")
def health(settings: SettingsDep) -> HealthOut:
    """Report that the process is running. Does not touch the database."""
    return HealthOut(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/health/ready", response_model=ReadinessOut, summary="Readiness check")
def readiness(session: SessionDep) -> ReadinessOut:
    """Verify database connectivity and that migrations have been applied."""
    try:
        session.execute(text("SELECT 1"))
        revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except SQLAlchemyError as exc:
        raise NotReadyError(
            "Database is not reachable or Alembic has not been applied.",
            details={"error": type(exc).__name__},
        ) from exc
    return ReadinessOut(status="ready", database="ok", alembic_revision=revision)
