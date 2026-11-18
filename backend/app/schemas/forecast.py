"""Forecast, vintage and as-of selection response models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.models.forecast import ForecastPoint, ForecastVintage
from app.repositories.forecast_selection_repository import SelectionRow, SelectionRow as _Row


class SelectedIntervalOut(BaseModel):
    """The decision-time forecast for one settlement period."""

    settlement_date: date
    settlement_period: int
    interval_start_utc: datetime
    local_start: str
    forecast_mw: float | None
    vintage_id: int | None
    vintage_publish_time_utc: datetime | None
    lead_time_minutes: int | None
    fallback_depth: int
    selection_status: str

    @classmethod
    def from_row(cls, row: SelectionRow, local_start: str) -> "SelectedIntervalOut":
        return cls(
            settlement_date=row.settlement_date,
            settlement_period=row.settlement_period,
            interval_start_utc=row.interval_start_utc,
            local_start=local_start,
            forecast_mw=None if row.forecast_mw is None else float(row.forecast_mw),
            vintage_id=row.vintage_id,
            vintage_publish_time_utc=row.vintage_publish_time_utc,
            lead_time_minutes=row.lead_time_minutes,
            fallback_depth=row.fallback_depth,
            selection_status=row.selection_status,
        )


class SelectedDaySummaryOut(BaseModel):
    """Aggregates for a delivery day's as-of forecast."""

    intervals: int
    selected: int
    missing: int
    total_forecast_mwh: float | None
    mean_forecast_mw: float | None
    min_lead_minutes: int | None
    max_lead_minutes: int | None


class SelectedDayOut(BaseModel):
    """Response payload for the selected day-ahead forecast."""

    delivery_date: date
    policy_code: str
    cutoff_definition: str
    cutoff_utc: datetime
    mapping: str
    summary: SelectedDaySummaryOut
    intervals: list[SelectedIntervalOut]


class VintageSummaryOut(BaseModel):
    """One stored vintage seen from a delivery day's perspective."""

    vintage_id: int
    publish_time_utc: datetime
    local_publish_time: str
    point_count: int
    resolution_minutes: int
    horizon_start_utc: datetime
    horizon_end_utc: datetime
    is_after_cutoff: bool
    is_used_at_cutoff: bool
    hours_in_delivery_day: int

    @classmethod
    def from_model(
        cls,
        vintage: ForecastVintage,
        *,
        local_publish_time: str,
        is_after_cutoff: bool,
        is_used_at_cutoff: bool,
        hours_in_delivery_day: int,
    ) -> "VintageSummaryOut":
        return cls(
            vintage_id=vintage.id,
            publish_time_utc=vintage.publish_time_utc,
            local_publish_time=local_publish_time,
            point_count=vintage.point_count,
            resolution_minutes=vintage.resolution_minutes,
            horizon_start_utc=vintage.horizon_start_utc,
            horizon_end_utc=vintage.horizon_end_utc,
            is_after_cutoff=is_after_cutoff,
            is_used_at_cutoff=is_used_at_cutoff,
            hours_in_delivery_day=hours_in_delivery_day,
        )


class VintageLineageOut(BaseModel):
    """Every vintage that could apply to a delivery day, ordered by publication."""

    delivery_date: date
    policy_code: str
    cutoff_utc: datetime
    vintages: list[VintageSummaryOut]
    note: str


class ForecastPointOut(BaseModel):
    """One native-resolution forecast point."""

    valid_from_utc: datetime
    valid_to_utc: datetime
    local_start: str
    generation_mw: float | None

    @classmethod
    def from_model(cls, point: ForecastPoint, local_start: str) -> "ForecastPointOut":
        return cls(
            valid_from_utc=point.valid_from_utc,
            valid_to_utc=point.valid_to_utc,
            local_start=local_start,
            generation_mw=None if point.generation_mw is None else float(point.generation_mw),
        )


class VintageDetailOut(BaseModel):
    """A vintage and all of its points."""

    vintage_id: int
    dataset: str
    publish_time_utc: datetime
    local_publish_time: str
    resolution_minutes: int
    horizon_start_utc: datetime
    horizon_end_utc: datetime
    point_count: int
    points: list[ForecastPointOut]
