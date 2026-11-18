"""Actual generation response models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.repositories.actual_generation_repository import ActualPoint


class ActualIntervalOut(BaseModel):
    """One settlement period of WIND outturn."""

    settlement_date: date
    settlement_period: int
    start_time_utc: datetime
    local_start: str
    generation_mw: float | None
    source_publish_time_utc: datetime

    @classmethod
    def from_domain(
        cls, point: ActualPoint, local_start: str
    ) -> "ActualIntervalOut":
        return cls(
            settlement_date=point.settlement_date,
            settlement_period=point.settlement_period,
            start_time_utc=point.start_time_utc,
            local_start=local_start,
            generation_mw=None if point.generation_mw is None else float(point.generation_mw),
            source_publish_time_utc=point.source_publish_time_utc,
        )


class DailyActualOut(BaseModel):
    """A settlement day aggregated from its latest-revision intervals."""

    settlement_date: date
    periods_with_data: int
    mean_mw: float | None
    total_mwh: float | None
