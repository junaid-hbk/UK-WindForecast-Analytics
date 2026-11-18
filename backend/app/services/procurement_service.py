"""Illustrative procurement scenario.

``additional procurement = demand scenario − forecast wind generation``

Positive = estimated shortfall (buy more), negative = potential surplus (sell or
reduce). This is deliberately *not* a purchasing recommendation: actual demand,
other generation sources, interconnector flows, losses and market prices are all
outside scope and are not supplied by the data this platform ingests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core import time as time_utils
from app.core.errors import InvalidRequestError
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.forecast_selection_repository import (
    AnalysisInterval,
    ForecastSelectionRepository,
)

DISCLAIMER = (
    "Illustrative estimate only. This is the arithmetic difference between the demand "
    "scenario you supplied and the day-ahead forecast wind generation available at the "
    "configured decision cutoff. It is not a complete electricity purchasing "
    "recommendation: actual demand, non-wind generation, interconnector flows, network "
    "losses and market prices are not part of this dataset."
)

SETTLEMENT_PERIOD_HOURS = Decimal("0.5")


@dataclass
class ProcurementInterval:
    """One settlement period of the scenario."""

    settlement_date: date
    settlement_period: int
    interval_start_utc: datetime
    local_start: str
    demand_mw: Decimal
    forecast_mw: Decimal | None
    delta_mw: Decimal | None
    classification: str
    vintage_publish_time_utc: datetime | None
    lead_time_minutes: int | None


@dataclass
class ProcurementScenario:
    """Scenario result with totals and an explicit availability count."""

    policy_code: str
    date_from: date
    date_to: date
    demand_mw: Decimal
    intervals: list[ProcurementInterval] = field(default_factory=list)
    total_demand_mwh: Decimal = Decimal("0")
    total_forecast_mwh: Decimal = Decimal("0")
    total_delta_mwh: Decimal = Decimal("0")
    shortfall_mwh: Decimal = Decimal("0")
    surplus_mwh: Decimal = Decimal("0")
    shortfall_intervals: int = 0
    surplus_intervals: int = 0
    balanced_intervals: int = 0
    unavailable_intervals: int = 0
    disclaimer: str = DISCLAIMER


class ProcurementService:
    """Compute the illustrative delta series for a demand scenario."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def scenario(
        self,
        *,
        demand_mw: Decimal,
        date_from: date,
        date_to: date,
        policy_code: str | None = None,
    ) -> ProcurementScenario:
        """Build the scenario for an inclusive settlement-date range."""
        if date_to < date_from:
            raise InvalidRequestError("date_to must not precede date_from")
        if demand_mw < 0:
            raise InvalidRequestError("demand_mw must be zero or positive")

        policy = CutoffPolicyRepository(self._session).resolve(policy_code)
        intervals = ForecastSelectionRepository(self._session).fetch_analysis_intervals(
            policy_id=policy.id, date_from=date_from, date_to=date_to
        )
        result = ProcurementScenario(
            policy_code=policy.code,
            date_from=date_from,
            date_to=date_to,
            demand_mw=demand_mw,
        )

        for interval in intervals:
            result.intervals.append(self._build_interval(interval, demand_mw, result))
        result.total_demand_mwh = _quantise(
            result.demand_mw * SETTLEMENT_PERIOD_HOURS * len(intervals)
        )
        result.total_forecast_mwh = _quantise(
            sum(
                (
                    (i.forecast_mw or Decimal("0")) * SETTLEMENT_PERIOD_HOURS
                    for i in result.intervals
                    if i.forecast_mw is not None
                ),
                Decimal("0"),
            )
        )
        result.total_delta_mwh = _quantise(
            sum(
                (i.delta_mw * SETTLEMENT_PERIOD_HOURS for i in result.intervals if i.delta_mw is not None),
                Decimal("0"),
            )
        )
        return result

    @staticmethod
    def _build_interval(
        interval: AnalysisInterval, demand_mw: Decimal, result: ProcurementScenario
    ) -> ProcurementInterval:
        forecast = interval.forecast_mw
        delta = None if forecast is None else demand_mw - forecast
        if delta is None:
            classification = "unavailable"
            result.unavailable_intervals += 1
        elif delta > 0:
            classification = "shortfall"
            result.shortfall_intervals += 1
            result.shortfall_mwh = _quantise(
                result.shortfall_mwh + delta * SETTLEMENT_PERIOD_HOURS
            )
        elif delta < 0:
            classification = "surplus"
            result.surplus_intervals += 1
            result.surplus_mwh = _quantise(
                result.surplus_mwh + (-delta) * SETTLEMENT_PERIOD_HOURS
            )
        else:
            classification = "balanced"
            result.balanced_intervals += 1

        return ProcurementInterval(
            settlement_date=interval.settlement_date,
            settlement_period=interval.settlement_period,
            interval_start_utc=interval.interval_start_utc,
            local_start=time_utils.to_london(interval.interval_start_utc).strftime(
                "%Y-%m-%d %H:%M %Z"
            ),
            demand_mw=demand_mw,
            forecast_mw=forecast,
            delta_mw=None if delta is None else _quantise(delta),
            classification=classification,
            vintage_publish_time_utc=interval.vintage_publish_time_utc,
            lead_time_minutes=interval.lead_time_minutes,
        )


def _quantise(value: Decimal) -> Decimal:
    """Round MW/MWh values to 2 decimal places, half-up, for presentation."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
