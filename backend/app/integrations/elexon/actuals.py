"""Normalisation of FUELHH actual generation responses.

Validation rules:

* only ``fuelType == "WIND"`` rows are kept (the request already filters, but the
  filter is also enforced client-side so a silently ignored query parameter can
  never corrupt the dataset);
* ``startTime`` is required and must parse as an ISO-8601 instant;
* ``generation`` may be ``null`` and is then stored as ``null`` — never as 0;
* the settlement date/period is derived from ``startTime`` in Europe/London and
  cross-checked against the API's own ``settlementDate`` / ``settlementPeriod``
  when present; a mismatch is rejected and reported, not reconciled silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from pydantic import ValidationError

from app.core import time as time_utils
from app.core.logging import get_logger
from app.integrations.elexon.client import ElexonClient
from app.integrations.elexon.errors import ElexonSchemaError
from app.integrations.elexon.schemas import FuelHhRow
from app.utils.chunking import date_chunks

logger = get_logger(__name__)

ACTUALS_PATH = "/datasets/FUELHH/stream"


@dataclass(frozen=True)
class NormalisedActual:
    """A validated FUELHH outturn value keyed to a settlement period."""

    settlement_date: date
    settlement_period: int
    start_time_utc: datetime
    end_time_utc: datetime
    generation_mw: Decimal | None
    publish_time_utc: datetime


@dataclass(frozen=True)
class RejectedRow:
    """A source row that failed validation, with the reason preserved."""

    reason: str
    detail: str


@dataclass
class ActualFetchResult:
    """Outcome of one or more FUELHH requests."""

    rows: list[NormalisedActual] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)
    requests: int = 0
    http_status: int | None = None


def fetch_wind_actuals(
    client: ElexonClient,
    date_from: date,
    date_to: date,
    *,
    chunk_days: int = 7,
) -> ActualFetchResult:
    """Fetch and normalise WIND outturn for an inclusive settlement-date range."""
    result = ActualFetchResult()
    seen: dict[tuple[date, int, datetime], NormalisedActual] = {}

    for chunk_from, chunk_to in date_chunks(date_from, date_to, chunk_days):
        params = {
            "settlementDateFrom": chunk_from.isoformat(),
            "settlementDateTo": chunk_to.isoformat(),
            "fuelType": "WIND",
        }
        raw_rows = client.get_rows(ACTUALS_PATH, params)
        result.requests += 1
        result.http_status = client.last_status

        try:
            parsed = [FuelHhRow.model_validate(row) for row in raw_rows]
        except ValidationError as exc:
            raise ElexonSchemaError(
                f"FUELHH payload for {chunk_from}..{chunk_to} did not match the documented "
                f"row shape: {exc.error_count()} validation error(s)"
            ) from exc

        for row in parsed:
            normalised = _normalise(row, result, chunk_from, chunk_to)
            if normalised is None:
                continue
            key = (normalised.settlement_date, normalised.settlement_period, normalised.publish_time_utc)
            if key in seen:
                result.rejected.append(
                    RejectedRow(
                        reason="duplicate_in_payload",
                        detail=(
                            f"{normalised.settlement_date} SP{normalised.settlement_period} "
                            f"published {normalised.publish_time_utc.isoformat()} appeared twice"
                        ),
                    )
                )
            seen[key] = normalised

    result.rows = sorted(seen.values(), key=lambda r: (r.settlement_date, r.settlement_period, r.publish_time_utc))
    logger.info(
        "elexon_actuals_fetched",
        extra={
            "rows": len(result.rows),
            "rejected": len(result.rejected),
            "requests": result.requests,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    return result


def _normalise(
    row: FuelHhRow,
    result: ActualFetchResult,
    chunk_from: date,
    chunk_to: date,
) -> NormalisedActual | None:
    if row.fuelType.upper() != "WIND":
        result.rejected.append(
            RejectedRow(
                reason="unexpected_fuel_type",
                detail=f"fuelType={row.fuelType!r} at {row.startTime.isoformat()}",
            )
        )
        return None

    try:
        settlement_date, settlement_period = time_utils.period_for_instant(row.startTime)
        start_utc, end_utc = time_utils.interval_for_period(settlement_date, settlement_period)
    except ValueError as exc:
        result.rejected.append(RejectedRow(reason="invalid_timestamp", detail=str(exc)))
        return None

    if row.settlementDate is not None and row.settlementDate != settlement_date:
        result.rejected.append(
            RejectedRow(
                reason="settlement_date_mismatch",
                detail=(
                    f"API says {row.settlementDate} SP{row.settlementPeriod} for "
                    f"{row.startTime.isoformat()}, derived {settlement_date} SP{settlement_period}"
                ),
            )
        )
        return None

    if row.settlementPeriod is not None and row.settlementPeriod != settlement_period:
        result.rejected.append(
            RejectedRow(
                reason="settlement_period_mismatch",
                detail=(
                    f"API says {row.settlementDate} SP{row.settlementPeriod} for "
                    f"{row.startTime.isoformat()}, derived {settlement_date} SP{settlement_period}"
                ),
            )
        )
        return None

    if not chunk_from <= settlement_date <= chunk_to:
        result.rejected.append(
            RejectedRow(
                reason="outside_requested_window",
                detail=f"{settlement_date} SP{settlement_period} outside {chunk_from}..{chunk_to}",
            )
        )
        return None

    return NormalisedActual(
        settlement_date=settlement_date,
        settlement_period=settlement_period,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        generation_mw=row.generation,
        publish_time_utc=row.publishTime,
    )
