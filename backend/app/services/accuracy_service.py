"""Forecast accuracy metrics.

Metric definitions (all computed on the *evaluated set* only — intervals where
both the as-of forecast and the actual exist):

* error ``e = forecast − actual`` in MW; **positive means over-forecast**.
* ``MAE = mean(|e|)``
* ``RMSE = sqrt(mean(e²))`` (same units as MW; penalises large misses)
* ``WAPE = 100 * Σ|e| / Σ|actual|`` — volume weighted, defined only when
  ``Σ|actual| > 0``. MAPE is intentionally not reported: wind output approaches
  zero, which makes percentage errors unbounded and misleading.
* ``bias = mean(e)`` (signed MW) and ``bias_pct = 100 * Σe / Σactual``.
* ``coverage = n_evaluated / n_expected``.

Missing values are never replaced by zero. Every exclusion is counted and
returned next to the metric, because a metric without its `n` is not a result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.errors import InvalidRequestError
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.forecast_selection_repository import (
    AnalysisInterval,
    ForecastSelectionRepository,
)

LEAD_TIME_EDGES: tuple[int, ...] = (0, 360, 720, 1080, 1440, 2160, 2880)
LEAD_TIME_LABELS: tuple[str, ...] = (
    "0-6h",
    "6-12h",
    "12-18h",
    "18-24h",
    "24-36h",
    "36-48h",
)
OVER_48H_LABEL = ">48h"
UNKNOWN_LEAD_LABEL = "unknown"
MINUTE_BUCKETS = ("0-6h", "6-12h", "12-18h", "18-24h", "24-36h", "36-48h", ">48h", "unknown")


@dataclass
class Metrics:
    """A complete metric block, including what was excluded."""

    mae_mw: float | None = None
    rmse_mw: float | None = None
    wape_pct: float | None = None
    bias_mw: float | None = None
    bias_pct: float | None = None
    n_evaluated: int = 0
    n_expected: int = 0
    n_missing_forecast: int = 0
    n_missing_actual: int = 0
    n_no_vintage_before_cutoff: int = 0
    n_duplicate_intervals: int = 0
    n_invalid_timestamps: int = 0
    coverage_pct: float | None = None
    insufficient_data: bool = True
    wape_note: str | None = None


@dataclass
class AccuracySummary:
    """Range-level accuracy result."""

    policy_code: str
    date_from: date
    date_to: date
    granularity: str
    metrics: Metrics
    notes: list[str] = field(default_factory=list)


@dataclass
class DailyAccuracy:
    """Per-settlement-day accuracy."""

    settlement_date: date
    metrics: Metrics
    accuracy_pct: float | None


@dataclass
class LeadTimeAccuracy:
    """Accuracy for one forecast lead-time bucket."""

    label: str
    lower_minutes: int | None
    upper_minutes: int | None
    metrics: Metrics
    is_empty: bool


class AccuracyService:
    """Compute forecast error statistics from the materialised analysis view."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── public API ───────────────────────────────────────────────────────
    def summary(
        self,
        date_from: date,
        date_to: date,
        *,
        policy_code: str | None = None,
        granularity: str = "sp",
    ) -> AccuracySummary:
        """Range-level metrics."""
        policy, frame = self._frame(date_from, date_to, policy_code, granularity)
        prepared = _prepare(frame, granularity=granularity)
        return AccuracySummary(
            policy_code=policy.code,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
            metrics=prepared.metrics,
            notes=prepared.notes,
        )

    def daily(
        self,
        date_from: date,
        date_to: date,
        *,
        policy_code: str | None = None,
        granularity: str = "sp",
    ) -> list[DailyAccuracy]:
        """Per-day metrics, including days with no evaluated intervals."""
        policy, frame = self._frame(date_from, date_to, policy_code, granularity)
        prepared = _prepare(frame, granularity=granularity)
        evaluated = prepared.evaluated

        results: list[DailyAccuracy] = []
        if evaluated.empty:
            return results

        for day, group in evaluated.groupby("settlement_date", dropna=False):
            metrics = _metrics_from_group(group)
            results.append(
                DailyAccuracy(
                    settlement_date=day,
                    metrics=metrics,
                    accuracy_pct=_accuracy_pct(metrics.wape_pct),
                )
            )
        return results

    def by_lead_time(
        self,
        date_from: date,
        date_to: date,
        *,
        policy_code: str | None = None,
        granularity: str = "sp",
    ) -> list[LeadTimeAccuracy]:
        """Metrics per lead-time bucket, with empty buckets included."""
        policy, frame = self._frame(date_from, date_to, policy_code, granularity)
        prepared = _prepare(frame, granularity=granularity)
        evaluated = prepared.evaluated
        buckets: list[LeadTimeAccuracy] = []

        if evaluated.empty:
            for index, label in enumerate(LEAD_TIME_LABELS):
                buckets.append(
                    LeadTimeAccuracy(
                        label=label,
                        lower_minutes=LEAD_TIME_EDGES[index],
                        upper_minutes=LEAD_TIME_EDGES[index + 1],
                        metrics=Metrics(n_expected=0),
                        is_empty=True,
                    )
                )
            buckets.append(
                LeadTimeAccuracy(
                    label=OVER_48H_LABEL,
                    lower_minutes=LEAD_TIME_EDGES[-1],
                    upper_minutes=None,
                    metrics=Metrics(n_expected=0),
                    is_empty=True,
                )
            )
            buckets.append(
                LeadTimeAccuracy(
                    label=UNKNOWN_LEAD_LABEL,
                    lower_minutes=None,
                    upper_minutes=None,
                    metrics=Metrics(n_expected=0),
                    is_empty=True,
                )
            )
            return buckets

        working = evaluated.copy()
        working["lead_bucket"] = _lead_bucket_labels(working["lead_time_minutes"])

        for index, label in enumerate(LEAD_TIME_LABELS):
            subset = working[working["lead_bucket"] == label]
            buckets.append(
                LeadTimeAccuracy(
                    label=label,
                    lower_minutes=LEAD_TIME_EDGES[index],
                    upper_minutes=LEAD_TIME_EDGES[index + 1],
                    metrics=_metrics_from_group(subset),
                    is_empty=subset.empty,
                )
            )

        over = working[working["lead_bucket"] == OVER_48H_LABEL]
        buckets.append(
            LeadTimeAccuracy(
                label=OVER_48H_LABEL,
                lower_minutes=LEAD_TIME_EDGES[-1],
                upper_minutes=None,
                metrics=_metrics_from_group(over),
                is_empty=over.empty,
            )
        )
        unknown = working[working["lead_bucket"] == UNKNOWN_LEAD_LABEL]
        buckets.append(
            LeadTimeAccuracy(
                label=UNKNOWN_LEAD_LABEL,
                lower_minutes=None,
                upper_minutes=None,
                metrics=_metrics_from_group(unknown),
                is_empty=unknown.empty,
            )
        )
        return buckets

    # ── internals ────────────────────────────────────────────────────────
    def _frame(
        self,
        date_from: date,
        date_to: date,
        policy_code: str | None,
        granularity: str,
    ) -> tuple[Any, pd.DataFrame]:
        if granularity not in ("sp", "hourly"):
            raise InvalidRequestError("granularity must be 'sp' or 'hourly'")
        if date_to < date_from:
            raise InvalidRequestError("date_to must not precede date_from")
        policy = CutoffPolicyRepository(self._session).resolve(policy_code)
        intervals = ForecastSelectionRepository(self._session).fetch_analysis_intervals(
            policy_id=policy.id, date_from=date_from, date_to=date_to
        )
        return policy, _to_frame(intervals)


@dataclass
class _Prepared:
    evaluated: pd.DataFrame
    metrics: Metrics
    notes: list[str]


def _to_frame(intervals: list[AnalysisInterval]) -> pd.DataFrame:
    """Build a typed frame; every conversion is explicit about failure."""
    if not intervals:
        return pd.DataFrame(
            columns=[
                "settlement_date",
                "settlement_period",
                "interval_start_utc",
                "lead_time_minutes",
                "forecast_mw",
                "actual_mw",
                "selection_status",
            ]
        )
    frame = pd.DataFrame(
        {
            "settlement_date": [i.settlement_date for i in intervals],
            "settlement_period": [i.settlement_period for i in intervals],
            "interval_start_utc": pd.to_datetime(
                [i.interval_start_utc for i in intervals], utc=True, errors="coerce"
            ),
            "lead_time_minutes": pd.to_numeric(
                pd.Series([i.lead_time_minutes for i in intervals], dtype="object"),
                errors="coerce",
            ),
            "forecast_mw": pd.to_numeric(
                pd.Series([i.forecast_mw for i in intervals], dtype="object"), errors="coerce"
            ),
            "actual_mw": pd.to_numeric(
                pd.Series([i.actual_mw for i in intervals], dtype="object"), errors="coerce"
            ),
            "selection_status": [i.selection_status for i in intervals],
        }
    )
    return frame


def _prepare(frame: pd.DataFrame, *, granularity: str) -> _Prepared:
    """Validate, de-duplicate and split the frame into expected vs evaluated."""
    notes: list[str] = []
    n_expected = int(len(frame))
    invalid_timestamps = 0
    duplicates = 0

    if frame.empty:
        return _Prepared(
            evaluated=frame.copy(),
            metrics=Metrics(n_expected=0, coverage_pct=None),
            notes=["No selection rows exist for this range and cutoff policy."],
        )

    working = frame.copy()
    invalid_mask = working["interval_start_utc"].isna()
    invalid_timestamps = int(invalid_mask.sum())
    if invalid_timestamps:
        working = working[~invalid_mask]
        notes.append(f"{invalid_timestamps} interval(s) had invalid timestamps and were excluded.")

    before = len(working)
    working = working.sort_values(["settlement_date", "settlement_period"]).drop_duplicates(
        subset=["settlement_date", "settlement_period"], keep="last"
    )
    duplicates = before - len(working)

    if granularity == "hourly":
        working = _to_hourly(working)

    n_missing_forecast = int(working["forecast_mw"].isna().sum())
    n_missing_actual = int(working["actual_mw"].isna().sum())
    n_no_vintage = int((working["selection_status"] != "selected").sum())

    evaluated = working.dropna(subset=["forecast_mw", "actual_mw"]).copy()

    metrics = _metrics(
        forecast=evaluated["forecast_mw"],
        actual=evaluated["actual_mw"],
        n_expected=len(working),
        n_missing_forecast=n_missing_forecast,
        n_missing_actual=n_missing_actual,
        n_no_vintage=n_no_vintage,
        n_duplicates=duplicates,
        n_invalid=invalid_timestamps,
    )

    if granularity == "sp":
        notes.append(
            "WINDFOR is published hourly and mapped onto half-hourly settlement periods "
            "(step mapping duplicates each hourly value across two periods); n at this "
            "granularity therefore counts duplicated forecast information."
        )
    if n_no_vintage:
        notes.append(
            f"{n_no_vintage} interval(s) had no vintage published at or before the cutoff."
        )
    return _Prepared(evaluated=evaluated, metrics=metrics, notes=notes)


def _to_hourly(frame: pd.DataFrame) -> pd.DataFrame:
    """Collapse to native forecast hours: first forecast, mean of available actuals."""
    working = frame.copy()
    working["hour_utc"] = working["interval_start_utc"].dt.floor("h")
    grouped = (
        working.sort_values(["settlement_date", "settlement_period"])
        .groupby("hour_utc", as_index=False)
        .agg(
            settlement_date=("settlement_date", "first"),
            settlement_period=("settlement_period", "first"),
            interval_start_utc=("hour_utc", "first"),
            lead_time_minutes=("lead_time_minutes", "first"),
            forecast_mw=("forecast_mw", "first"),
            actual_mw=("actual_mw", "mean"),
            selection_status=("selection_status", "first"),
        )
    )
    return grouped


def _metrics_from_group(group: pd.DataFrame) -> Metrics:
    return _metrics(
        forecast=group["forecast_mw"],
        actual=group["actual_mw"],
        n_expected=int(len(group)),
        n_missing_forecast=int(group["forecast_mw"].isna().sum()),
        n_missing_actual=int(group["actual_mw"].isna().sum()),
        n_no_vintage=int((group["selection_status"] != "selected").sum()),
        n_duplicates=0,
        n_invalid=0,
    )


def _metrics(
    *,
    forecast: pd.Series,
    actual: pd.Series,
    n_expected: int,
    n_missing_forecast: int,
    n_missing_actual: int,
    n_no_vintage: int,
    n_duplicates: int,
    n_invalid: int,
) -> Metrics:
    """Compute the metric block. Emptiness and zero denominators are explicit."""
    n = int(len(forecast))
    coverage = round(100.0 * n / n_expected, 3) if n_expected else None

    if n == 0:
        return Metrics(
            n_evaluated=0,
            n_expected=n_expected,
            n_missing_forecast=n_missing_forecast,
            n_missing_actual=n_missing_actual,
            n_no_vintage_before_cutoff=n_no_vintage,
            n_duplicate_intervals=n_duplicates,
            n_invalid_timestamps=n_invalid,
            coverage_pct=coverage,
            insufficient_data=True,
            wape_note="No interval has both a forecast and an actual.",
        )

    errors = forecast.to_numpy(dtype="float64") - actual.to_numpy(dtype="float64")
    absolute_actual = float(np.abs(actual.to_numpy(dtype="float64")).sum())
    actual_sum = float(actual.to_numpy(dtype="float64").sum())

    wape: float | None = None
    wape_note: str | None = None
    if absolute_actual > 0:
        wape = round(100.0 * float(np.abs(errors).sum()) / absolute_actual, 3)
    else:
        wape_note = "ZERO_ACTUAL_ENERGY: the sum of |actual| is zero, so WAPE is undefined."

    bias_pct: float | None = None
    if actual_sum != 0:
        bias_pct = round(100.0 * float(errors.sum()) / actual_sum, 3)

    return Metrics(
        mae_mw=round(float(np.abs(errors).mean()), 3),
        rmse_mw=round(float(np.sqrt(np.square(errors).mean())), 3),
        wape_pct=wape,
        bias_mw=round(float(errors.mean()), 3),
        bias_pct=bias_pct,
        n_evaluated=n,
        n_expected=n_expected,
        n_missing_forecast=n_missing_forecast,
        n_missing_actual=n_missing_actual,
        n_no_vintage_before_cutoff=n_no_vintage,
        n_duplicate_intervals=n_duplicates,
        n_invalid_timestamps=n_invalid,
        coverage_pct=coverage,
        insufficient_data=False,
        wape_note=wape_note,
    )


def _lead_bucket_labels(lead_times: pd.Series) -> pd.Series:
    """Assign each observation to a lead-time bucket label."""
    labels = pd.Series(UNKNOWN_LEAD_LABEL, index=lead_times.index, dtype="object")
    numeric = pd.to_numeric(lead_times, errors="coerce")
    valid = numeric.notna()

    binned = pd.cut(
        numeric[valid],
        bins=list(LEAD_TIME_EDGES) + [np.inf],
        labels=list(LEAD_TIME_LABELS) + [OVER_48H_LABEL],
        right=False,
    )
    labels.loc[valid] = binned.astype("object").to_numpy()
    return labels


def _accuracy_pct(wape_pct: float | None) -> float | None:
    """Derived convenience figure: 100 − WAPE, clamped to [0, 100]."""
    if wape_pct is None:
        return None
    return round(max(0.0, min(100.0, 100.0 - wape_pct)), 3)
