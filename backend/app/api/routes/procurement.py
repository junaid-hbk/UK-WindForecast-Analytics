"""Illustrative procurement scenario endpoint."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter

from app.api.deps import SessionDep, SettingsDep
from app.api.validation import ensure_date_range
from app.schemas.common import Envelope
from app.schemas.procurement import (
    ProcurementIntervalOut,
    ProcurementRequest,
    ProcurementResponse,
    ProcurementTotalsOut,
)
from app.services.procurement_service import ProcurementScenario, ProcurementService

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _totals(scenario: ProcurementScenario) -> ProcurementTotalsOut:
    evaluated = len(scenario.intervals) - scenario.unavailable_intervals
    return ProcurementTotalsOut(
        intervals=len(scenario.intervals),
        evaluated_intervals=evaluated,
        unavailable_intervals=scenario.unavailable_intervals,
        shortfall_intervals=scenario.shortfall_intervals,
        surplus_intervals=scenario.surplus_intervals,
        balanced_intervals=scenario.balanced_intervals,
        total_demand_mwh=float(scenario.total_demand_mwh),
        total_forecast_mwh=float(scenario.total_forecast_mwh),
        total_delta_mwh=float(scenario.total_delta_mwh),
        shortfall_mwh=float(scenario.shortfall_mwh),
        surplus_mwh=float(scenario.surplus_mwh),
    )


@router.post(
    "/scenario",
    response_model=Envelope[ProcurementResponse],
    summary="Illustrative procurement delta for a demand scenario",
)
def procurement_scenario(
    request: ProcurementRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> Envelope[ProcurementResponse]:
    """Compute ``demand scenario − forecast wind generation`` per interval.

    Positive is an estimated shortfall, negative a potential surplus. The
    response always carries the illustrative-only disclaimer; this is not a
    complete purchasing recommendation.
    """
    ensure_date_range(request.date_from, request.date_to, settings.max_query_days)
    scenario = ProcurementService(session).scenario(
        demand_mw=Decimal(request.demand_mw),
        date_from=request.date_from,
        date_to=request.date_to,
        policy_code=request.cutoff_policy,
    )
    payload = ProcurementResponse(
        policy_code=scenario.policy_code,
        date_from=scenario.date_from,
        date_to=scenario.date_to,
        demand_mw=float(scenario.demand_mw),
        totals=_totals(scenario),
        intervals=(
            [
                ProcurementIntervalOut(
                    settlement_date=interval.settlement_date,
                    settlement_period=interval.settlement_period,
                    interval_start_utc=interval.interval_start_utc,
                    local_start=interval.local_start,
                    demand_mw=float(interval.demand_mw),
                    forecast_mw=(
                        None if interval.forecast_mw is None else float(interval.forecast_mw)
                    ),
                    delta_mw=None if interval.delta_mw is None else float(interval.delta_mw),
                    classification=interval.classification,
                    vintage_publish_time_utc=interval.vintage_publish_time_utc,
                    lead_time_minutes=interval.lead_time_minutes,
                )
                for interval in scenario.intervals
            ]
            if request.include_intervals
            else []
        ),
        disclaimer=scenario.disclaimer,
    )
    return Envelope(
        data=payload,
        meta={
            "kind": "illustrative_estimate",
            "sign_convention": "positive delta = estimated shortfall, negative = potential surplus",
            "energy_conversion": "MW x 0.5 h per settlement period",
            "excluded_inputs": [
                "actual demand",
                "non-wind generation",
                "interconnector flows",
                "network losses",
                "prices",
            ],
        },
    )
