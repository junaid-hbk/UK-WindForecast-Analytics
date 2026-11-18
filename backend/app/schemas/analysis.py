"""Accuracy response models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.services.accuracy_service import (
    AccuracySummary,
    DailyAccuracy,
    LeadTimeAccuracy,
    Metrics,
)


class MetricsOut(BaseModel):
    """Metric block plus everything that was excluded from it."""

    mae_mw: float | None
    rmse_mw: float | None
    wape_pct: float | None
    bias_mw: float | None
    bias_pct: float | None
    n_evaluated: int
    n_expected: int
    n_missing_forecast: int
    n_missing_actual: int
    n_no_vintage_before_cutoff: int
    n_duplicate_intervals: int
    n_invalid_timestamps: int
    coverage_pct: float | None
    insufficient_data: bool
    wape_note: str | None

    @classmethod
    def from_domain(cls, metrics: Metrics) -> "MetricsOut":
        return cls(**metrics.__dict__)


class AccuracySummaryOut(BaseModel):
    """Range-level accuracy."""

    policy_code: str
    date_from: date
    date_to: date
    granularity: str
    metrics: MetricsOut
    notes: list[str]

    @classmethod
    def from_domain(cls, summary: AccuracySummary) -> "AccuracySummaryOut":
        return cls(
            policy_code=summary.policy_code,
            date_from=summary.date_from,
            date_to=summary.date_to,
            granularity=summary.granularity,
            metrics=MetricsOut.from_domain(summary.metrics),
            notes=summary.notes,
        )


class DailyAccuracyOut(BaseModel):
    """One settlement day of accuracy."""

    settlement_date: date
    metrics: MetricsOut
    accuracy_pct: float | None

    @classmethod
    def from_domain(cls, row: DailyAccuracy) -> "DailyAccuracyOut":
        return cls(
            settlement_date=row.settlement_date,
            metrics=MetricsOut.from_domain(row.metrics),
            accuracy_pct=row.accuracy_pct,
        )


class LeadTimeAccuracyOut(BaseModel):
    """Accuracy for one lead-time bucket."""

    label: str
    lower_minutes: int | None
    upper_minutes: int | None
    is_empty: bool
    metrics: MetricsOut

    @classmethod
    def from_domain(cls, row: LeadTimeAccuracy) -> "LeadTimeAccuracyOut":
        return cls(
            label=row.label,
            lower_minutes=row.lower_minutes,
            upper_minutes=row.upper_minutes,
            is_empty=row.is_empty,
            metrics=MetricsOut.from_domain(row.metrics),
        )
