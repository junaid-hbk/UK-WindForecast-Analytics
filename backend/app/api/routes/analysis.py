"""Forecast accuracy endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import SessionDep, SettingsDep
from app.api.validation import ensure_date_range
from app.schemas.analysis import (
    AccuracySummaryOut,
    DailyAccuracyOut,
    LeadTimeAccuracyOut,
)
from app.schemas.common import Envelope
from app.services.accuracy_service import AccuracyService

router = APIRouter(prefix="/analysis", tags=["forecast accuracy"])

Granularity = Literal["sp", "hourly"]


@router.get(
    "/accuracy",
    response_model=Envelope[AccuracySummaryOut],
    summary="Forecast accuracy for a date range",
)
def accuracy_summary(
    session: SessionDep,
    settings: SettingsDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    cutoff_policy: str | None = Query(default=None),
    granularity: Granularity = Query(default="sp"),
) -> Envelope[AccuracySummaryOut]:
    """MAE, RMSE, WAPE, bias and observation counts over the evaluated set."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    summary = AccuracyService(session).summary(
        date_from, date_to, policy_code=cutoff_policy, granularity=granularity
    )
    return Envelope(
        data=AccuracySummaryOut.from_domain(summary),
        meta={
            "granularity": granularity,
            "definitions": "see /api/v1/meta/config",
            "missing_data_policy": "excluded and counted; never imputed",
        },
    )


@router.get(
    "/accuracy/daily",
    response_model=Envelope[list[DailyAccuracyOut]],
    summary="Daily forecast accuracy",
)
def accuracy_daily(
    session: SessionDep,
    settings: SettingsDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    cutoff_policy: str | None = Query(default=None),
    granularity: Granularity = Query(default="sp"),
) -> Envelope[list[DailyAccuracyOut]]:
    """Per-settlement-day metrics, including a derived accuracy percentage."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    rows = AccuracyService(session).daily(
        date_from, date_to, policy_code=cutoff_policy, granularity=granularity
    )
    return Envelope(
        data=[DailyAccuracyOut.from_domain(row) for row in rows],
        meta={
            "days": len(rows),
            "accuracy_pct": "100 - WAPE, clamped to [0, 100]; a convenience, not a KPI claim",
            "note": "Days with no evaluated intervals are omitted rather than reported as zero.",
        },
    )


@router.get(
    "/accuracy/by-lead-time",
    response_model=Envelope[list[LeadTimeAccuracyOut]],
    summary="Forecast accuracy by lead time",
)
def accuracy_by_lead_time(
    session: SessionDep,
    settings: SettingsDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    cutoff_policy: str | None = Query(default=None),
    granularity: Granularity = Query(default="sp"),
) -> Envelope[list[LeadTimeAccuracyOut]]:
    """Metrics per lead-time bucket, with empty buckets returned explicitly."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    rows = AccuracyService(session).by_lead_time(
        date_from, date_to, policy_code=cutoff_policy, granularity=granularity
    )
    return Envelope(
        data=[LeadTimeAccuracyOut.from_domain(row) for row in rows],
        meta={
            "lead_time_definition": "delivery interval start minus the chosen vintage publishTime",
            "buckets": "half-open [lower, upper) in minutes; >48h and unknown are separate",
            "empty_buckets": "returned with n=0 so charts keep a stable shape",
        },
    )
