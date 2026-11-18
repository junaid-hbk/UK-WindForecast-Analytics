"""Procurement arithmetic: MW → MW·h conversion, sign convention and availability.

The service reads the materialised analysis view; these tests replace that read
with explicit intervals so the arithmetic can be checked without mixing in
selection behaviour (which has its own suite).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.repositories.forecast_selection_repository import (
    AnalysisInterval,
    ForecastSelectionRepository,
)
from app.services.procurement_service import ProcurementService

DAY = date(2026, 1, 15)
CUTOFF = datetime(2026, 1, 14, 9, 20, tzinfo=timezone.utc)


def _interval(period: int, forecast: Decimal | None) -> AnalysisInterval:
    return AnalysisInterval(
        settlement_date=DAY,
        settlement_period=period,
        interval_start_utc=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        cutoff_utc=CUTOFF,
        vintage_publish_time_utc=CUTOFF,
        lead_time_minutes=990,
        forecast_mw=forecast,
        actual_mw=None,
        selection_status="selected" if forecast is not None else "no_point_for_interval",
    )


def _scenario(session, monkeypatch, intervals: list[AnalysisInterval], demand: str):
    monkeypatch.setattr(
        ForecastSelectionRepository,
        "fetch_analysis_intervals",
        lambda self, **kwargs: intervals,
    )
    return ProcurementService(session).scenario(
        demand_mw=Decimal(demand), date_from=DAY, date_to=DAY
    )


def test_energy_is_mw_times_half_an_hour(session, monkeypatch) -> None:
    intervals = [_interval(1, Decimal("1000")), _interval(2, Decimal("3000"))]
    result = _scenario(session, monkeypatch, intervals, "2000")

    # (1000 + 3000) MW × 0.5 h = 2,000 MW·h
    assert result.total_forecast_mwh == Decimal("2000.00")
    # (1000 + -1000) MW × 0.5 h = 0 MW·h
    assert result.total_delta_mwh == Decimal("0.00")
    assert result.shortfall_intervals == 1
    assert result.surplus_intervals == 1
    assert result.shortfall_mwh == Decimal("500.00")
    assert result.surplus_mwh == Decimal("500.00")
    assert result.intervals[0].classification == "shortfall"
    assert result.intervals[1].classification == "surplus"


def test_unavailable_forecast_is_counted_and_excluded_from_energy(session, monkeypatch) -> None:
    intervals = [_interval(1, Decimal("1000")), _interval(2, None)]
    result = _scenario(session, monkeypatch, intervals, "2000")

    assert result.unavailable_intervals == 1
    # Only the available interval contributes to forecast and delta energy.
    assert result.total_forecast_mwh == Decimal("500.00")
    assert result.total_delta_mwh == Decimal("500.00")
    unavailable = result.intervals[1]
    assert unavailable.forecast_mw is None
    assert unavailable.delta_mw is None
    assert unavailable.classification == "unavailable"
