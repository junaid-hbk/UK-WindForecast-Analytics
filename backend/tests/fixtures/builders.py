"""Explicit builders for test data.

These are small, readable helpers — deliberately not a random-data factory.
Nothing here is production data: every value is a hand-written fixture.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from app.core import time as time_utils
from app.models.actual import ActualGeneration
from app.models.forecast import ForecastPoint, ForecastVintage


def hourly_points(
    start_utc: datetime,
    hours: int,
    value: Decimal | Callable[[datetime], Decimal | None],
) -> dict[datetime, Decimal | None]:
    """Build a contiguous hourly point series."""
    points: dict[datetime, Decimal | None] = {}
    for offset in range(hours):
        moment = start_utc + timedelta(hours=offset)
        points[moment] = value(moment) if callable(value) else value
    return points


def add_vintage(
    session: Session,
    *,
    publish_time_utc: datetime,
    points: dict[datetime, Decimal | None],
    resolution_minutes: int = 60,
) -> ForecastVintage:
    """Insert a vintage and its points, mirroring what ingestion would store."""
    starts = sorted(points)
    if not starts:
        raise ValueError("a vintage needs at least one point")
    step = timedelta(minutes=resolution_minutes)
    vintage = ForecastVintage(
        dataset="WINDFOR",
        publish_time_utc=publish_time_utc,
        horizon_start_utc=starts[0],
        horizon_end_utc=starts[-1] + step,
        resolution_minutes=resolution_minutes,
        point_count=len(starts),
        source_row_count=len(starts),
    )
    session.add(vintage)
    session.flush()
    session.add_all(
        [
            ForecastPoint(
                vintage_id=vintage.id,
                valid_from_utc=start,
                valid_to_utc=start + step,
                generation_mw=points[start],
            )
            for start in starts
        ]
    )
    session.flush()
    return vintage


def add_actual(
    session: Session,
    *,
    settlement_date: date,
    settlement_period: int,
    generation_mw: Decimal | None,
    publish_time_utc: datetime | None = None,
) -> ActualGeneration:
    """Insert one actual-generation revision for a settlement period."""
    start, end = time_utils.interval_for_period(settlement_date, settlement_period)
    record = ActualGeneration(
        settlement_date=settlement_date,
        settlement_period=settlement_period,
        fuel_type="WIND",
        start_time_utc=start,
        end_time_utc=end,
        generation_mw=generation_mw,
        source_publish_time_utc=publish_time_utc or (end + timedelta(minutes=30)),
    )
    session.add(record)
    session.flush()
    return record


def fuelhh_row(
    *,
    settlement_date: date,
    settlement_period: int,
    generation: int | None,
    publish_time: datetime | None = None,
) -> dict[str, object]:
    """A FUELHH stream row exactly as the API returns it."""
    start, _end = time_utils.interval_for_period(settlement_date, settlement_period)
    return {
        "dataset": "FUELHH",
        "publishTime": (publish_time or start).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "settlementDate": settlement_date.isoformat(),
        "settlementPeriod": settlement_period,
        "fuelType": "WIND",
        "generation": generation,
    }


def windfor_row(
    *, publish_time: datetime, start_time: datetime, generation: int | None
) -> dict[str, object]:
    """A WINDFOR stream row exactly as the API returns it."""
    return {
        "dataset": "WINDFOR",
        "publishTime": publish_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generation": generation,
    }
