"""Procurement scenario request/response models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProcurementRequest(BaseModel):
    """A demand scenario supplied by the user."""

    demand_mw: Decimal = Field(
        ge=0,
        le=Decimal("100000"),
        description="Constant demand scenario in MW applied to every interval in the range.",
        examples=[12000],
    )
    date_from: date = Field(description="Inclusive GB settlement date.")
    date_to: date = Field(description="Inclusive GB settlement date.")
    cutoff_policy: str | None = Field(
        default=None, description="Cutoff policy code; defaults to the configured default."
    )
    include_intervals: bool = Field(
        default=True, description="Return per-interval detail in addition to totals."
    )


class ProcurementIntervalOut(BaseModel):
    """One interval of the illustrative delta."""

    settlement_date: date
    settlement_period: int
    interval_start_utc: datetime
    local_start: str
    demand_mw: float
    forecast_mw: float | None
    delta_mw: float | None
    classification: str
    vintage_publish_time_utc: datetime | None
    lead_time_minutes: int | None


class ProcurementTotalsOut(BaseModel):
    """Range totals in MW·h (MW × 0.5 h per settlement period)."""

    intervals: int
    evaluated_intervals: int
    unavailable_intervals: int
    shortfall_intervals: int
    surplus_intervals: int
    balanced_intervals: int
    total_demand_mwh: float
    total_forecast_mwh: float
    total_delta_mwh: float
    shortfall_mwh: float
    surplus_mwh: float


class ProcurementResponse(BaseModel):
    """Scenario result, always carrying the illustrative-only disclaimer."""

    policy_code: str
    date_from: date
    date_to: date
    demand_mw: float
    totals: ProcurementTotalsOut
    intervals: list[ProcurementIntervalOut]
    disclaimer: str
