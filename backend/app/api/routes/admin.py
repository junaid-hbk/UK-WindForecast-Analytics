"""Administrative ingestion and rebuild endpoints.

Guarded by ``X-Admin-Token``. They run synchronously, so callers should request
bounded windows (the CLI is the right tool for a multi-month backfill).
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, SettingsDep, require_admin
from app.api.validation import ensure_date_range
from app.core import time as time_utils
from app.db.session import get_session_factory
from app.integrations.elexon.client import ElexonClient
from app.schemas.common import Envelope
from app.schemas.data_status import IngestionSummaryOut
from app.services.forecast_selection_service import ForecastSelectionService, SelectionRebuildSummary
from app.services.ingestion_service import IngestionService

router = APIRouter(
    prefix="/admin", tags=["administration"], dependencies=[Depends(require_admin)]
)


def _client(settings: SettingsDep) -> ElexonClient:
    return ElexonClient(
        base_url=settings.elexon_base_url,
        connect_timeout_seconds=settings.elexon_connect_timeout_seconds,
        read_timeout_seconds=settings.elexon_read_timeout_seconds,
        max_attempts=settings.elexon_max_attempts,
        backoff_base_seconds=settings.elexon_backoff_base_seconds,
        backoff_max_seconds=settings.elexon_backoff_max_seconds,
        user_agent=settings.elexon_user_agent,
    )


@router.post(
    "/ingest/actuals",
    response_model=Envelope[IngestionSummaryOut],
    summary="Ingest FUELHH WIND actuals for a settlement-date range",
)
def ingest_actuals(
    settings: SettingsDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
) -> Envelope[IngestionSummaryOut]:
    """Run an incremental or small backfill of actual generation."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    client = _client(settings)
    try:
        summary = IngestionService(
            get_session_factory(),
            client,
            actual_chunk_days=settings.elexon_actual_chunk_days,
        ).ingest_actuals(date_from, date_to, run_type="manual")
    finally:
        client.close()
    return Envelope(data=IngestionSummaryOut.from_summary(summary), meta={"dataset": "FUELHH"})


@router.post(
    "/ingest/forecasts",
    response_model=Envelope[IngestionSummaryOut],
    summary="Ingest WINDFOR vintages for a publish-time window",
)
def ingest_forecasts(
    settings: SettingsDep,
    publish_from: datetime = Query(),
    publish_to: datetime = Query(),
) -> Envelope[IngestionSummaryOut]:
    """Discover and store every vintage published inside the window."""
    window_from = time_utils.ensure_utc(publish_from)
    window_to = time_utils.ensure_utc(publish_to)
    if window_to <= window_from:
        ensure_date_range(window_to.date(), window_from.date(), settings.max_query_days)
    client = _client(settings)
    try:
        summary = IngestionService(
            get_session_factory(),
            client,
            forecast_chunk_days=settings.elexon_forecast_chunk_days,
        ).ingest_forecasts(window_from, window_to, run_type="manual")
    finally:
        client.close()
    return Envelope(data=IngestionSummaryOut.from_summary(summary), meta={"dataset": "WINDFOR"})


@router.post(
    "/selections/rebuild",
    response_model=Envelope[dict],
    summary="Rebuild materialised as-of selections",
)
def rebuild_selections(
    session: SessionDep,
    settings: SettingsDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    cutoff_policy: str | None = Query(default=None),
) -> Envelope[dict]:
    """Recompute the decision-time forecast for every interval in the range."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    summary: SelectionRebuildSummary = ForecastSelectionService(
        session, mapping=settings.windfor_sp_mapping
    ).rebuild(date_from, date_to, policy_code=cutoff_policy)
    return Envelope(
        data={
            "policy_code": summary.policy_code,
            "cutoff_definition": summary.cutoff_definition,
            "date_from": summary.date_from.isoformat(),
            "date_to": summary.date_to.isoformat(),
            "mapping": summary.mapping,
            "intervals": summary.intervals,
            "selected": summary.selected,
            "no_vintage_before_cutoff": summary.no_vintage_before_cutoff,
            "no_point_for_interval": summary.no_point_for_interval,
            "fallback_intervals": summary.fallback_intervals,
            "max_fallback_depth": summary.max_fallback_depth,
            "min_lead_minutes": summary.min_lead_minutes,
            "max_lead_minutes": summary.max_lead_minutes,
            "vintages_considered": summary.vintages_considered,
            "days_with_missing_intervals": summary.missing_days,
        },
        meta={"look_ahead_safe": True},
    )
