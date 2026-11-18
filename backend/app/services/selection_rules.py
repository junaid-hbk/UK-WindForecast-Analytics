"""Pure forecast-selection rules (no database, no I/O).

Keeping this logic pure is what makes look-ahead bias testable: the only inputs
are a bucket start, a cutoff instant and the (immutable) published vintages.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from app.core import time as time_utils

MappingMode = Literal["step", "linear"]

STATUS_SELECTED = "selected"
STATUS_NO_VINTAGE = "no_vintage_before_cutoff"
STATUS_NO_POINT = "no_point_for_interval"


@dataclass(frozen=True)
class VintageSeries:
    """A vintage that can be queried for a delivery instant."""

    vintage_id: int
    publish_time_utc: datetime
    points: Mapping[datetime, Decimal | None]

    def __post_init__(self) -> None:
        if self.publish_time_utc.tzinfo is None:
            raise ValueError("publish_time_utc must be timezone-aware (UTC)")


@dataclass(frozen=True)
class SelectionOutcome:
    """What the decision-time view of one delivery interval is."""

    status: str
    vintage_id: int | None
    publish_time_utc: datetime | None
    generation_mw: Decimal | None
    lead_time_minutes: int | None
    fallback_depth: int
    covers_interval: bool


def value_for_interval(
    series: VintageSeries, interval_start_utc: datetime, mapping: MappingMode = "step"
) -> tuple[bool, Decimal | None]:
    """Resolve a vintage's value for a delivery interval.

    Returns ``(covered, value)``. ``covered`` distinguishes "this vintage has
    nothing for this interval" from "this vintage forecasts ``null`` MW here",
    which are different facts and must not be conflated.

    ``step``: WINDFOR is hourly, so the value valid at the start of the containing
    hour is used for both settlement periods in that hour. This adds no
    information that Elexon did not publish.
    ``linear``: interpolate at the interval midpoint between the surrounding
    hourly points; requires both endpoints, otherwise falls back to the step
    value when one exists.
    """
    start = time_utils.ensure_utc(interval_start_utc)
    hour = time_utils.floor_to_hour(start)
    if mapping == "step":
        if hour not in series.points:
            return False, None
        return True, series.points[hour]

    next_hour = hour + timedelta(hours=1)
    if mapping not in ("step", "linear"):
        raise ValueError(f"unsupported mapping mode {mapping!r}")
    if hour in series.points and next_hour in series.points:
        left = series.points[hour]
        right = series.points[next_hour]
        if left is None or right is None:
            return True, left
        midpoint_fraction = Decimal("0.5")
        return True, left + (right - left) * midpoint_fraction
    if hour in series.points:
        return True, series.points[hour]
    return False, None


def choose_as_of(
    interval_start_utc: datetime,
    cutoff_utc: datetime,
    candidates: Sequence[VintageSeries],
    *,
    mapping: MappingMode = "step",
) -> SelectionOutcome:
    """Choose the latest vintage published at or before the cutoff.

    ``candidates`` may be in any order; each eligible vintage is considered once.
    A vintage published after ``cutoff_utc`` is never considered — the comparison
    below is the single place look-ahead could be introduced, so it is strict and
    covered by tests.

    A vintage published after the interval itself started is also unusable as a
    forecast (its lead time would be negative), so it is skipped.
    """
    start = time_utils.ensure_utc(interval_start_utc)
    cutoff = time_utils.ensure_utc(cutoff_utc)
    eligible = [
        series
        for series in candidates
        if time_utils.ensure_utc(series.publish_time_utc) <= cutoff
    ]
    if not eligible:
        return SelectionOutcome(
            status=STATUS_NO_VINTAGE,
            vintage_id=None,
            publish_time_utc=None,
            generation_mw=None,
            lead_time_minutes=None,
            fallback_depth=0,
            covers_interval=False,
        )

    ordered = sorted(
        eligible,
        key=lambda series: (time_utils.ensure_utc(series.publish_time_utc), series.vintage_id),
        reverse=True,
    )

    depth = 0
    for series in ordered:
        publish = time_utils.ensure_utc(series.publish_time_utc)
        if publish > start:
            # Newer than the delivery instant: not a forecast for it.
            depth += 1
            continue
        covered, value = value_for_interval(series, start, mapping)
        if not covered:
            depth += 1
            continue
        lead_minutes = int((start - publish).total_seconds() // 60)
        return SelectionOutcome(
            status=STATUS_SELECTED,
            vintage_id=series.vintage_id,
            publish_time_utc=publish,
            generation_mw=value,
            lead_time_minutes=lead_minutes,
            fallback_depth=depth,
            covers_interval=True,
        )

    return SelectionOutcome(
        status=STATUS_NO_POINT,
        vintage_id=None,
        publish_time_utc=None,
        generation_mw=None,
        lead_time_minutes=None,
        fallback_depth=depth,
        covers_interval=False,
    )
