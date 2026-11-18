"""Normalisation of WINDFOR forecast responses into vintages.

A WINDFOR query filtered by ``publishDateTimeFrom/To`` returns the rows of every
vintage published inside that window, each with its complete horizon. Rows are
grouped by ``publishTime`` into vintages; nothing is merged or overwritten.

WINDFOR is **hourly** (verified: 73 points, exactly 60 minutes apart). The
resolution is measured from the payload rather than assumed, and rows that do not
sit on the vintage's grid are rejected and reported.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from pydantic import ValidationError

from app.core import time as time_utils
from app.core.logging import get_logger
from app.integrations.elexon.client import ElexonClient
from app.integrations.elexon.errors import ElexonSchemaError
from app.integrations.elexon.schemas import WindForRow
from app.utils.chunking import datetime_chunks

logger = get_logger(__name__)

FORECASTS_PATH = "/datasets/WINDFOR/stream"
DEFAULT_RESOLUTION_MINUTES = 60


@dataclass(frozen=True)
class NormalisedPoint:
    """One hourly forecast value inside a vintage."""

    valid_from_utc: datetime
    valid_to_utc: datetime
    generation_mw: Decimal | None


@dataclass
class NormalisedVintage:
    """A single published forecast file."""

    publish_time_utc: datetime
    resolution_minutes: int
    points: list[NormalisedPoint] = field(default_factory=list)
    source_row_count: int = 0
    http_status: int | None = None

    @property
    def horizon_start_utc(self) -> datetime:
        return self.points[0].valid_from_utc

    @property
    def horizon_end_utc(self) -> datetime:
        return self.points[-1].valid_to_utc


@dataclass(frozen=True)
class RejectedRow:
    """A forecast row that failed validation."""

    reason: str
    detail: str


@dataclass
class ForecastFetchResult:
    """Outcome of one or more WINDFOR requests."""

    vintages: list[NormalisedVintage] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)
    requests: int = 0
    http_status: int | None = None


def fetch_forecast_vintages(
    client: ElexonClient,
    publish_from: datetime,
    publish_to: datetime,
    *,
    chunk_days: int = 1,
) -> ForecastFetchResult:
    """Fetch every WINDFOR vintage published in ``[publish_from, publish_to)``."""
    result = ForecastFetchResult()
    grouped: dict[datetime, list[WindForRow]] = defaultdict(list)

    for chunk_from, chunk_to in datetime_chunks(
        time_utils.ensure_utc(publish_from), time_utils.ensure_utc(publish_to), chunk_days
    ):
        params = {
            "publishDateTimeFrom": chunk_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": chunk_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        raw_rows = client.get_rows(FORECASTS_PATH, params)
        result.requests += 1
        result.http_status = client.last_status

        try:
            parsed = [WindForRow.model_validate(row) for row in raw_rows]
        except ValidationError as exc:
            raise ElexonSchemaError(
                f"WINDFOR payload for {chunk_from}..{chunk_to} did not match the documented "
                f"row shape: {exc.error_count()} validation error(s)"
            ) from exc

        for row in parsed:
            if not chunk_from <= row.publishTime < chunk_to:
                # The API filtered on the window; a row outside it indicates the
                # filter was ignored. Refuse rather than silently widening scope.
                result.rejected.append(
                    RejectedRow(
                        reason="outside_requested_window",
                        detail=(
                            f"publishTime {row.publishTime.isoformat()} outside "
                            f"{chunk_from.isoformat()}..{chunk_to.isoformat()}"
                        ),
                    )
                )
                continue
            grouped[row.publishTime].append(row)

    for publish_time in sorted(grouped):
        vintage = _build_vintage(publish_time, grouped[publish_time], result)
        if vintage is not None:
            result.vintages.append(vintage)

    logger.info(
        "elexon_forecast_vintages_fetched",
        extra={
            "vintages": len(result.vintages),
            "points": sum(len(v.points) for v in result.vintages),
            "rejected": len(result.rejected),
            "requests": result.requests,
            "publish_from": time_utils.format_utc(publish_from),
            "publish_to": time_utils.format_utc(publish_to),
        },
    )
    return result


def _build_vintage(
    publish_time: datetime,
    rows: list[WindForRow],
    result: ForecastFetchResult,
) -> NormalisedVintage | None:
    if not rows:
        return None

    unique: dict[datetime, WindForRow] = {}
    for row in rows:
        if row.startTime in unique:
            result.rejected.append(
                RejectedRow(
                    reason="duplicate_in_payload",
                    detail=(
                        f"vintage {publish_time.isoformat()} repeated startTime "
                        f"{row.startTime.isoformat()}"
                    ),
                )
            )
        unique[row.startTime] = row

    start_times = sorted(unique)
    resolution = _detect_resolution(start_times, publish_time, result)
    if resolution is None:
        return None

    step = timedelta(minutes=resolution)
    points: list[NormalisedPoint] = []
    for start_time in start_times:
        if (start_time - start_times[0]) % step != timedelta(0) or start_time.minute % resolution != 0:
            result.rejected.append(
                RejectedRow(
                    reason="off_grid_point",
                    detail=(
                        f"vintage {publish_time.isoformat()} startTime "
                        f"{start_time.isoformat()} is not on a {resolution}-minute grid"
                    ),
                )
            )
            continue
        points.append(
            NormalisedPoint(
                valid_from_utc=start_time,
                valid_to_utc=start_time + step,
                generation_mw=unique[start_time].generation,
            )
        )

    if not points:
        return None

    expected = int((points[-1].valid_to_utc - points[0].valid_from_utc) / step)
    if expected != len(points):
        result.rejected.append(
            RejectedRow(
                reason="short_horizon",
                detail=(
                    f"vintage {publish_time.isoformat()} has {len(points)} of {expected} expected "
                    f"{resolution}-minute points"
                ),
            )
        )

    return NormalisedVintage(
        publish_time_utc=publish_time,
        resolution_minutes=resolution,
        points=points,
        source_row_count=len(rows),
    )


def _detect_resolution(
    start_times: list[datetime], publish_time: datetime, result: ForecastFetchResult
) -> int | None:
    if len(start_times) < 2:
        result.rejected.append(
            RejectedRow(
                reason="single_point_vintage",
                detail=(
                    f"vintage {publish_time.isoformat()} has {len(start_times)} point(s); "
                    "resolution cannot be measured"
                ),
            )
        )
        return None
    deltas = Counter(
        int((start_times[i] - start_times[i - 1]).total_seconds() // 60)
        for i in range(1, len(start_times))
    )
    resolution, _count = deltas.most_common(1)[0]
    if resolution <= 0:
        result.rejected.append(
            RejectedRow(
                reason="invalid_resolution",
                detail=f"vintage {publish_time.isoformat()} has non-positive point spacing",
            )
        )
        return None
    return resolution
