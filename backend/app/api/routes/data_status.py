"""Data status, ingestion history and data-quality endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import SessionDep, SettingsDep
from app.api.validation import ensure_date_range
from app.repositories.data_quality_repository import DataQualityRepository
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.schemas.common import Envelope, PaginationMeta
from app.schemas.data_status import (
    DataQualityIssueOut,
    DataStatusOut,
    IngestionRunOut,
)
from app.services.data_status_service import DataStatusService

router = APIRouter(prefix="/data", tags=["data status"])


@router.get(
    "/status",
    response_model=Envelope[DataStatusOut],
    summary="Coverage, freshness and ingestion health",
)
def get_status(
    session: SessionDep,
    settings: SettingsDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    cutoff_policy: str | None = Query(default=None),
) -> Envelope[DataStatusOut]:
    """Report what data exists, how fresh it is, and where the gaps are."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    status = DataStatusService(session).get_status(
        date_from=date_from, date_to=date_to, policy_code=cutoff_policy
    )
    return Envelope(
        data=DataStatusOut.from_domain(status),
        meta={"issues_are_explicit": True, "stale_threshold_days": 2},
    )


@router.get(
    "/runs",
    response_model=Envelope[list[IngestionRunOut]],
    summary="Ingestion run history",
)
def list_runs(
    session: SessionDep,
    limit: int = Query(default=25, ge=1, le=200),
    dataset: str | None = Query(default=None, pattern="^(FUELHH|WINDFOR)$"),
) -> Envelope[list[IngestionRunOut]]:
    """Return the most recent ingestion attempts, newest first."""
    runs = IngestionRunRepository(session).recent(limit=limit, dataset=dataset)
    return Envelope(
        data=[IngestionRunOut.from_model(run) for run in runs],
        meta={"pagination": PaginationMeta(limit=limit, offset=0, total=len(runs), returned=len(runs)).model_dump()},
    )


@router.get(
    "/issues",
    response_model=Envelope[list[DataQualityIssueOut]],
    summary="Data-quality issues",
)
def list_issues(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=500),
    severity: str | None = Query(default=None, pattern="^(info|warning|error)$"),
) -> Envelope[list[DataQualityIssueOut]]:
    """Return recorded data problems, newest first."""
    issues = DataQualityRepository(session).recent(limit=limit, severity=severity)
    return Envelope(
        data=[DataQualityIssueOut.from_model(issue) for issue in issues],
        meta={"returned": len(issues), "severity_filter": severity},
    )
