"""Forecast endpoints: as-of selection, vintage lineage and raw vintage detail."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Path, Query

from app.api.deps import SessionDep, SettingsDep
from app.core import time as time_utils
from app.core.errors import DataUnavailableError, NotFoundError
from app.models.cutoff import CutoffPolicy
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.forecast_selection_repository import ForecastSelectionRepository
from app.repositories.forecast_vintage_repository import ForecastVintageRepository
from app.schemas.common import Envelope
from app.schemas.forecast import (
    ForecastPointOut,
    SelectedDayOut,
    SelectedDaySummaryOut,
    SelectedIntervalOut,
    VintageDetailOut,
    VintageLineageOut,
    VintageSummaryOut,
)

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _cutoff(settings: SettingsDep, policy: CutoffPolicy, delivery_date: date):
    del settings  # settings kept in the signature for symmetry with other helpers
    tz = ZoneInfo(policy.timezone_id)
    return time_utils.resolve_cutoff(
        delivery_date, policy.local_time, offset_days=policy.offset_days, tz=tz
    )


def _cutoff_definition(policy: CutoffPolicy) -> str:
    return (
        f"{policy.local_time.strftime('%H:%M')} {policy.timezone_id} on "
        f"delivery_date{policy.offset_days:+d} day"
    )


@router.get(
    "/latest",
    response_model=Envelope[SelectedDayOut],
    summary="Selected day-ahead forecast for a delivery day",
)
def get_selected_day(
    session: SessionDep,
    settings: SettingsDep,
    delivery_date: date = Query(description="GB settlement date of delivery"),
    cutoff_policy: str | None = Query(default=None, description="Policy code; default if omitted"),
) -> Envelope[SelectedDayOut]:
    """Return the stored as-of forecast for each settlement period of a delivery day.

    Rows are produced by the selection rebuild, so the response reflects exactly
    what was available at the decision cutoff. If no selection exists yet the API
    answers 409 rather than inventing a forecast.
    """
    policy = CutoffPolicyRepository(session).resolve(cutoff_policy)
    rows = ForecastSelectionRepository(session).fetch_day_selections(
        policy_id=policy.id, delivery_date=delivery_date
    )
    if not rows:
        raise DataUnavailableError(
            f"No forecast selection stored for {delivery_date.isoformat()} under policy "
            f"{policy.code}. Build it first.",
            details={
                "delivery_date": delivery_date.isoformat(),
                "policy": policy.code,
                "action": "POST /api/v1/admin/selections/rebuild",
            },
        )

    cutoff = _cutoff(settings, policy, delivery_date)
    selected_values = [float(r.forecast_mw) for r in rows if r.forecast_mw is not None]
    leads = [r.lead_time_minutes for r in rows if r.lead_time_minutes is not None]
    payload = SelectedDayOut(
        delivery_date=delivery_date,
        policy_code=policy.code,
        cutoff_definition=_cutoff_definition(policy),
        cutoff_utc=cutoff,
        mapping=settings.windfor_sp_mapping,
        summary=SelectedDaySummaryOut(
            intervals=len(rows),
            selected=sum(1 for r in rows if r.selection_status == "selected"),
            missing=sum(1 for r in rows if r.selection_status != "selected"),
            total_forecast_mwh=(
                round(sum(selected_values) * 0.5, 3) if selected_values else None
            ),
            mean_forecast_mw=(
                round(sum(selected_values) / len(selected_values), 3) if selected_values else None
            ),
            min_lead_minutes=min(leads) if leads else None,
            max_lead_minutes=max(leads) if leads else None,
        ),
        intervals=[
            SelectedIntervalOut.from_row(
                row,
                time_utils.to_london(row.interval_start_utc).strftime("%Y-%m-%d %H:%M %Z"),
            )
            for row in rows
        ],
    )
    return Envelope(
        data=payload,
        meta={
            "note": (
                "Each interval uses the latest vintage published at or before the cutoff; "
                "null forecast_mw means no eligible vintage covered that interval."
            ),
            "look_ahead_safe": True,
        },
    )


@router.get(
    "/vintages",
    response_model=Envelope[VintageLineageOut],
    summary="All forecast vintages relevant to a delivery day",
)
def list_vintages(
    session: SessionDep,
    settings: SettingsDep,
    delivery_date: date = Query(description="GB settlement date of delivery"),
    cutoff_policy: str | None = Query(default=None),
) -> Envelope[VintageLineageOut]:
    """Show every vintage that could apply to a delivery day, flagged by cutoff."""
    policy = CutoffPolicyRepository(session).resolve(cutoff_policy)
    cutoff = _cutoff(settings, policy, delivery_date)
    day_start = time_utils.settlement_day_start_utc(delivery_date)
    day_end = time_utils.settlement_day_end_utc(delivery_date)

    vintage_repo = ForecastVintageRepository(session)
    vintages = vintage_repo.list_for_publish_window(
        publish_from=day_start - timedelta(days=3), publish_to=day_end + timedelta(days=1)
    )
    used_ids = {
        row.vintage_id
        for row in ForecastSelectionRepository(session).fetch_day_selections(
            policy_id=policy.id, delivery_date=delivery_date
        )
        if row.vintage_id is not None
    }

    summaries = []
    for vintage in vintages:
        points = vintage_repo.load_points(vintage.id)
        hours_in_day = sum(1 for point in points if day_start <= point.valid_from_utc < day_end)
        summaries.append(
            VintageSummaryOut.from_model(
                vintage,
                local_publish_time=time_utils.to_london(vintage.publish_time_utc).strftime(
                    "%Y-%m-%d %H:%M %Z"
                ),
                is_after_cutoff=vintage.publish_time_utc > cutoff,
                is_used_at_cutoff=vintage.id in used_ids,
                hours_in_delivery_day=hours_in_day,
            )
        )

    payload = VintageLineageOut(
        delivery_date=delivery_date,
        policy_code=policy.code,
        cutoff_utc=cutoff,
        vintages=summaries,
        note=(
            "Vintages published after cutoff_utc are historical only: they were not, and "
            "cannot be, used for the day-ahead decision."
        ),
    )
    return Envelope(data=payload, meta={"vintages": len(summaries), "used": len(used_ids)})


@router.get(
    "/vintages/{vintage_id}",
    response_model=Envelope[VintageDetailOut],
    summary="One vintage with its native-resolution points",
)
def get_vintage(
    session: SessionDep,
    vintage_id: int = Path(ge=1),
) -> Envelope[VintageDetailOut]:
    """Return a single stored vintage exactly as published (hourly)."""
    repo = ForecastVintageRepository(session)
    vintage = repo.get_by_id(vintage_id)
    if vintage is None:
        raise NotFoundError(f"Vintage {vintage_id} is not stored.")

    points = repo.load_points(vintage_id)
    payload = VintageDetailOut(
        vintage_id=vintage.id,
        dataset=vintage.dataset,
        publish_time_utc=vintage.publish_time_utc,
        local_publish_time=time_utils.to_london(vintage.publish_time_utc).strftime(
            "%Y-%m-%d %H:%M %Z"
        ),
        resolution_minutes=vintage.resolution_minutes,
        horizon_start_utc=vintage.horizon_start_utc,
        horizon_end_utc=vintage.horizon_end_utc,
        point_count=vintage.point_count,
        points=[
            ForecastPointOut.from_model(
                point,
                time_utils.to_london(point.valid_from_utc).strftime("%Y-%m-%d %H:%M %Z"),
            )
            for point in points
        ],
    )
    return Envelope(data=payload, meta={"points": len(points)})
