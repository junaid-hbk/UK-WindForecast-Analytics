"""Metric definitions: exact arithmetic, missing data, and zero denominators."""

from __future__ import annotations

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from app.services.accuracy_service import (
    _lead_bucket_labels,
    _metrics,
    _prepare,
    _to_frame,
    _to_hourly,
)
from app.repositories.forecast_selection_repository import AnalysisInterval


def _series(values: list[float | None]) -> pd.Series:
    return pd.Series(values, dtype="float64")


def _metrics_for(forecasts: list[float], actuals: list[float]):  # noqa: ANN202
    return _metrics(
        forecast=_series(forecasts),
        actual=_series(actuals),
        n_expected=len(forecasts),
        n_missing_forecast=0,
        n_missing_actual=0,
        n_no_vintage=0,
        n_duplicates=0,
        n_invalid=0,
    )


class TestPointMetrics:
    def test_mae_rmse_wape_and_bias(self) -> None:
        # errors: +20, 0 -> |e| sum 20, sum actual 140
        metrics = _metrics_for([100.0, 60.0], [80.0, 60.0])
        assert metrics.mae_mw == pytest.approx(10.0)
        assert metrics.rmse_mw == pytest.approx(float(np.sqrt(200.0)), abs=1e-3)
        assert metrics.wape_pct == pytest.approx(14.286, abs=1e-3)
        assert metrics.bias_mw == pytest.approx(10.0)
        assert metrics.bias_pct == pytest.approx(14.286, abs=1e-3)
        assert metrics.n_evaluated == 2
        assert metrics.insufficient_data is False

    def test_perfect_forecast(self) -> None:
        metrics = _metrics_for([500.0, 600.0], [500.0, 600.0])
        assert metrics.mae_mw == 0.0
        assert metrics.rmse_mw == 0.0
        assert metrics.wape_pct == 0.0
        assert metrics.bias_mw == 0.0

    def test_negative_bias_means_under_forecast(self) -> None:
        metrics = _metrics_for([80.0, 80.0], [100.0, 100.0])
        assert metrics.bias_mw == pytest.approx(-20.0)
        assert metrics.wape_pct == pytest.approx(20.0)

    def test_wape_is_volume_weighted_not_a_mean_of_percentages(self) -> None:
        # 100 error on a 1000 MW interval and 1 error on a 1 MW interval.
        metrics = _metrics_for([1100.0, 2.0], [1000.0, 1.0])
        assert metrics.wape_pct == pytest.approx(100 * 101 / 1001, abs=1e-3)


class TestDegenerateInputs:
    def test_zero_actual_denominator_returns_null_wape(self) -> None:
        metrics = _metrics_for([5.0, 5.0], [0.0, 0.0])
        assert metrics.wape_pct is None
        assert metrics.wape_note is not None
        assert metrics.wape_note.startswith("ZERO_ACTUAL_ENERGY")
        assert metrics.n_evaluated == 2
        assert metrics.insufficient_data is False

    def test_empty_evaluated_set(self) -> None:
        metrics = _metrics(
            forecast=_series([]),
            actual=_series([]),
            n_expected=4,
            n_missing_forecast=2,
            n_missing_actual=2,
            n_no_vintage=2,
            n_duplicates=0,
            n_invalid=0,
        )
        assert metrics.mae_mw is None
        assert metrics.wape_pct is None
        assert metrics.insufficient_data is True
        assert metrics.n_evaluated == 0
        assert metrics.n_missing_forecast == 2
        assert metrics.coverage_pct == 0.0

    def test_negative_actuals_are_kept_and_handled(self) -> None:
        metrics = _metrics_for([10.0], [-20.0])
        assert metrics.wape_pct == pytest.approx(150.0)
        assert metrics.bias_mw == pytest.approx(30.0)


def _interval(
    *,
    day: date = date(2026, 1, 15),
    period: int = 1,
    forecast: float | None = 100.0,
    actual: float | None = 80.0,
    lead: int | None = 600,
    start: datetime | None = None,
    status: str = "selected",
) -> AnalysisInterval:
    return AnalysisInterval(
        settlement_date=day,
        settlement_period=period,
        interval_start_utc=start or datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        cutoff_utc=datetime(2026, 1, 14, 9, 20, tzinfo=timezone.utc),
        vintage_publish_time_utc=datetime(2026, 1, 14, 8, 0, tzinfo=timezone.utc),
        lead_time_minutes=lead,
        forecast_mw=forecast,  # type: ignore[arg-type]
        actual_mw=actual,  # type: ignore[arg-type]
        selection_status=status,
    )


class TestFramePreparation:
    def test_missing_values_are_excluded_and_counted(self) -> None:
        frame = _to_frame(
            [
                _interval(period=1, forecast=100.0, actual=80.0),
                _interval(period=2, forecast=None, actual=90.0, status="no_point_for_interval"),
                _interval(period=3, forecast=60.0, actual=None),
            ]
        )
        prepared = _prepare(frame, granularity="sp")
        metrics = prepared.metrics
        assert metrics.n_expected == 3
        assert metrics.n_evaluated == 1
        assert metrics.n_missing_forecast == 1
        assert metrics.n_missing_actual == 1
        assert metrics.n_no_vintage_before_cutoff == 1
        assert metrics.coverage_pct == pytest.approx(33.333, abs=1e-3)
        assert metrics.mae_mw == pytest.approx(20.0)

    def test_duplicate_settlement_intervals_are_collapsed(self) -> None:
        frame = _to_frame(
            [
                _interval(period=1, forecast=100.0, actual=80.0),
                _interval(period=1, forecast=110.0, actual=80.0),
            ]
        )
        prepared = _prepare(frame, granularity="sp")
        assert prepared.metrics.n_duplicate_intervals == 1
        assert prepared.metrics.n_evaluated == 1
        assert prepared.metrics.bias_mw == pytest.approx(30.0)  # keeps the last row

    def test_invalid_timestamps_are_excluded_and_counted(self) -> None:
        frame = _to_frame([_interval()])
        frame.loc[0, "interval_start_utc"] = pd.NaT
        prepared = _prepare(frame, granularity="sp")
        assert prepared.metrics.n_invalid_timestamps == 1
        assert prepared.metrics.n_evaluated == 0
        assert any("invalid timestamps" in note for note in prepared.notes)

    def test_empty_frame_reports_insufficient_data(self) -> None:
        prepared = _prepare(_to_frame([]), granularity="sp")
        assert prepared.metrics.insufficient_data is True
        assert prepared.metrics.n_expected == 0
        assert prepared.notes

    def test_hourly_granularity_collapses_pairs_of_periods(self) -> None:
        frame = _to_frame(
            [
                _interval(
                    period=1,
                    forecast=100.0,
                    actual=80.0,
                    start=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
                ),
                _interval(
                    period=2,
                    forecast=100.0,
                    actual=90.0,
                    start=datetime(2026, 1, 15, 0, 30, tzinfo=timezone.utc),
                ),
            ]
        )
        hourly = _to_hourly(frame)
        assert len(hourly) == 1
        assert hourly.iloc[0]["actual_mw"] == pytest.approx(85.0)
        assert hourly.iloc[0]["forecast_mw"] == pytest.approx(100.0)


class TestLeadTimeBuckets:
    @pytest.mark.parametrize(
        ("minutes", "expected"),
        [
            (0, "0-6h"),
            (359, "0-6h"),
            (360, "6-12h"),
            (1080, "18-24h"),
            (2879, "36-48h"),
            (2880, ">48h"),
            (5000, ">48h"),
        ],
    )
    def test_bucket_boundaries(self, minutes: int, expected: str) -> None:
        labels = _lead_bucket_labels(pd.Series([minutes], dtype="float64"))
        assert labels.iloc[0] == expected

    def test_missing_lead_time_is_unknown(self) -> None:
        labels = _lead_bucket_labels(pd.Series([np.nan], dtype="float64"))
        assert labels.iloc[0] == "unknown"
