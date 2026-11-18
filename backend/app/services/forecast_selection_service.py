"""Build the materialised as-of forecast selection.

The service composes three things: the settlement calendar (``app.core.time``),
the immutable vintages loaded by the repository, and the pure selection rules in
``app.services.selection_rules``. It never reads anything published after the
configured cutoff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core import time as time_utils
from app.core.logging import get_logger
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.data_quality_repository import DataQualityRepository, QualityIssue
from app.repositories.forecast_selection_repository import (
    ForecastSelectionRepository,
    SelectionRow,
)
from app.repositories.forecast_vintage_repository import ForecastVintageRepository
from app.services.selection_rules import (
    STATUS_NO_POINT,
    STATUS_NO_VINTAGE,
    MappingMode,
    VintageSeries,
    choose_as_of,
)

logger = get_logger(__name__)


@dataclass
class SelectionRebuildSummary:
    """Outcome of rebuilding selections for a policy and date range."""

    policy_code: str
    cutoff_definition: str
    date_from: date
    date_to: date
    mapping: str
    intervals: int = 0
    selected: int = 0
    no_vintage_before_cutoff: int = 0
    no_point_for_interval: int = 0
    fallback_intervals: int = 0
    max_fallback_depth: int = 0
    min_lead_minutes: int | None = None
    max_lead_minutes: int | None = None
    vintages_considered: int = 0
    missing_days: list[str] = field(default_factory=list)


class ForecastSelectionService:
    """Persist the decision-time forecast for every delivery interval in a range."""

    def __init__(self, session: Session, *, mapping: MappingMode = "step") -> None:
        if mapping not in ("step", "linear"):
            raise ValueError(f"unsupported mapping mode {mapping!r}")
        self._session = session
        self._mapping = mapping

    def rebuild(
        self,
        date_from: date,
        date_to: date,
        *,
        policy_code: str | None = None,
    ) -> SelectionRebuildSummary:
        """Rebuild (and replace) selection rows for ``[date_from, date_to]``."""
        if date_to < date_from:
            raise ValueError("date_to must not precede date_from")

        policy = CutoffPolicyRepository(self._session).resolve(policy_code)
        tz = self._timezone(policy.timezone_id)
        days = self._days(date_from, date_to)

        earliest_start = time_utils.settlement_day_start_utc(date_from)
        # The load window must cover the *whole* last delivery day. Using the
        # start of that day would leave every period after 00:30 with no points
        # loaded, silently turning them into "no forecast" rows.
        latest_end = time_utils.settlement_day_end_utc(date_to)
        cutoff_by_day = {
            day: time_utils.resolve_cutoff(
                day, policy.local_time, offset_days=policy.offset_days, tz=tz
            )
            for day in days
        }
        cutoff_ceiling = max(cutoff_by_day.values())

        inputs = ForecastVintageRepository(self._session).load_selection_inputs(
            earliest_bucket_utc=time_utils.floor_to_hour(earliest_start),
            latest_bucket_utc=time_utils.floor_to_hour(latest_end),
            cutoff_ceiling_utc=cutoff_ceiling,
        )
        candidates = [
            VintageSeries(
                vintage_id=vintage_id,
                publish_time_utc=publish_time,
                points=inputs.points.get(vintage_id, {}),
            )
            for vintage_id, publish_time in inputs.vintages.items()
        ]

        rows: list[SelectionRow] = []
        summary = SelectionRebuildSummary(
            policy_code=policy.code,
            cutoff_definition=(
                f"{policy.local_time.strftime('%H:%M')} {policy.timezone_id} "
                f"on delivery_date{policy.offset_days:+d} day"
            ),
            date_from=date_from,
            date_to=date_to,
            mapping=self._mapping,
            vintages_considered=len(candidates),
        )

        for day in days:
            cutoff = cutoff_by_day[day]
            periods = time_utils.settlement_periods_in_day(day)
            day_missing = 0
            for period in range(1, periods + 1):
                start, _end = time_utils.interval_for_period(day, period)
                outcome = choose_as_of(
                    start,
                    cutoff,
                    candidates,
                    mapping=self._mapping,
                )
                rows.append(
                    SelectionRow(
                        settlement_date=day,
                        settlement_period=period,
                        interval_start_utc=start,
                        cutoff_utc=cutoff,
                        vintage_id=outcome.vintage_id,
                        vintage_publish_time_utc=outcome.publish_time_utc,
                        lead_time_minutes=outcome.lead_time_minutes,
                        forecast_mw=outcome.generation_mw,
                        fallback_depth=outcome.fallback_depth,
                        selection_status=outcome.status,
                    )
                )
                summary.intervals += 1
                if outcome.status == "selected":
                    summary.selected += 1
                elif outcome.status == STATUS_NO_VINTAGE:
                    summary.no_vintage_before_cutoff += 1
                    day_missing += 1
                elif outcome.status == STATUS_NO_POINT:
                    summary.no_point_for_interval += 1
                    day_missing += 1
                if outcome.fallback_depth:
                    summary.fallback_intervals += 1
                    summary.max_fallback_depth = max(
                        summary.max_fallback_depth, outcome.fallback_depth
                    )
                if outcome.lead_time_minutes is not None:
                    current_min = summary.min_lead_minutes
                    current_max = summary.max_lead_minutes
                    summary.min_lead_minutes = (
                        outcome.lead_time_minutes
                        if current_min is None
                        else min(current_min, outcome.lead_time_minutes)
                    )
                    summary.max_lead_minutes = (
                        outcome.lead_time_minutes
                        if current_max is None
                        else max(current_max, outcome.lead_time_minutes)
                    )
            if day_missing:
                summary.missing_days.append(day.isoformat())

        ForecastSelectionRepository(self._session).replace_range(
            policy_id=policy.id,
            date_from=date_from,
            date_to=date_to,
            rows=rows,
        )
        self._record_missing(rows, policy.code)
        self._session.flush()

        logger.info(
            "forecast_selection_rebuilt",
            extra={
                "policy": policy.code,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "intervals": summary.intervals,
                "selected": summary.selected,
                "missing": summary.no_vintage_before_cutoff + summary.no_point_for_interval,
            },
        )
        return summary

    def _record_missing(self, rows: list[SelectionRow], policy_code: str) -> None:
        """One aggregated issue per day, rather than one per interval."""
        by_day: dict[date, dict[str, int]] = {}
        for row in rows:
            if row.selection_status == "selected":
                continue
            by_day.setdefault(row.settlement_date, {})
            by_day[row.settlement_date][row.selection_status] = (
                by_day[row.settlement_date].get(row.selection_status, 0) + 1
            )

        issues: list[QualityIssue] = []
        for day, counts in sorted(by_day.items()):
            for status, count in sorted(counts.items()):
                issues.append(
                    QualityIssue(
                        dataset="WINDFOR",
                        issue_type=status.upper(),
                        severity="warning",
                        settlement_date=day,
                        detail=(
                            f"{count} interval(s) on {day.isoformat()} had no usable forecast "
                            f"for cutoff policy {policy_code} ({status})"
                        ),
                    )
                )
        if issues:
            DataQualityRepository(self._session).add_many(issues)

    @staticmethod
    def _timezone(timezone_id: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_id)
        except ZoneInfoNotFoundError as exc:  # pragma: no cover - configuration guard
            raise ValueError(f"unknown timezone {timezone_id!r} in cutoff policy") from exc

    @staticmethod
    def _days(date_from: date, date_to: date) -> list[date]:
        total = (date_to - date_from).days
        return [date_from + timedelta(days=offset) for offset in range(total + 1)]


def coerce_mw(value: Decimal | None) -> float | None:
    """Convert a stored MW value to float for analysis layers."""
    return None if value is None else float(value)
