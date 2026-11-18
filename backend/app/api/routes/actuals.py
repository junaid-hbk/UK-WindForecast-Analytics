"""Actual generation endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import SessionDep, SettingsDep
from app.api.validation import ensure_date_range, ensure_pagination
from app.core import time as time_utils
from app.repositories.actual_generation_repository import ActualGenerationRepository
from app.schemas.actuals import ActualIntervalOut, DailyActualOut
from app.schemas.common import Envelope, PaginationMeta

router = APIRouter(prefix="/actuals", tags=["actual generation"])


@router.get(
    "",
    response_model=Envelope[list[ActualIntervalOut]],
    summary="Half-hourly WIND outturn (latest revision per settlement period)",
)
def list_actuals(
    session: SessionDep,
    settings: SettingsDep,
    date_from: date = Query(alias="from", description="Inclusive GB settlement date"),
    date_to: date = Query(alias="to", description="Inclusive GB settlement date"),
    limit: int = Query(default=1500, ge=1),
    offset: int = Query(default=0, ge=0),
) -> Envelope[list[ActualIntervalOut]]:
    """Return actual national wind generation for a settlement-date range."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    ensure_pagination(limit, offset, settings.page_size_max)

    repo = ActualGenerationRepository(session)
    points = repo.latest_for_range(date_from, date_to)
    total = len(points)
    page = points[offset : offset + limit]
    data = [
        ActualIntervalOut.from_domain(
            point, time_utils.to_london(point.start_time_utc).strftime("%Y-%m-%d %H:%M %Z")
        )
        for point in page
    ]
    return Envelope(
        data=data,
        meta={
            "pagination": PaginationMeta(
                limit=limit, offset=offset, total=total, returned=len(data)
            ).model_dump(),
            "policy": "latest revision per settlement period (v_actual_generation_latest)",
            "missing_values": "null generation is preserved and never replaced with 0",
        },
    )


@router.get(
    "/daily",
    response_model=Envelope[list[DailyActualOut]],
    summary="Daily WIND outturn totals",
)
def list_actuals_daily(
    session: SessionDep,
    settings: SettingsDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
) -> Envelope[list[DailyActualOut]]:
    """Aggregate outturn per settlement day (MW average and MW·h)."""
    ensure_date_range(date_from, date_to, settings.max_query_days)
    repo = ActualGenerationRepository(session)
    points = repo.latest_for_range(date_from, date_to)

    per_day: dict[date, list[float]] = {}
    for point in points:
        if point.generation_mw is None:
            continue
        per_day.setdefault(point.settlement_date, []).append(float(point.generation_mw))

    data = [
        DailyActualOut(
            settlement_date=day,
            periods_with_data=len(values),
            mean_mw=round(sum(values) / len(values), 3) if values else None,
            total_mwh=round(sum(values) * 0.5, 3) if values else None,
        )
        for day, values in sorted(per_day.items())
    ]
    return Envelope(
        data=data,
        meta={"days": len(data), "note": "Only non-null outturn values contribute to totals."},
    )
