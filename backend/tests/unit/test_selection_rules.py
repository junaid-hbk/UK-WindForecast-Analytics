"""Forecast selection rules: the look-ahead-bias boundary.

These tests are the formal proof that a forecast published after the decision
cutoff can never be selected, and that the selection otherwise picks the newest
eligible vintage that actually covers the interval.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.services.selection_rules import (
    STATUS_NO_POINT,
    STATUS_NO_VINTAGE,
    STATUS_SELECTED,
    VintageSeries,
    choose_as_of,
    value_for_interval,
)

CUTOFF = datetime(2026, 1, 14, 9, 20, tzinfo=timezone.utc)
INTERVAL = datetime(2026, 1, 15, 6, 0, tzinfo=timezone.utc)


def series(
    vintage_id: int,
    publish: datetime,
    hours: dict[datetime, Decimal | None] | None = None,
    *,
    start: datetime = datetime(2026, 1, 14, 21, 0, tzinfo=timezone.utc),
    count: int = 48,
    value: Decimal = Decimal("1000"),
) -> VintageSeries:
    """Build a vintage covering a 48-hour hourly horizon."""
    if hours is None:
        hours = {start + timedelta(hours=offset): value for offset in range(count)}
    return VintageSeries(vintage_id=vintage_id, publish_time_utc=publish, points=hours)


class TestLookAheadPrevention:
    def test_newest_vintage_before_cutoff_wins(self) -> None:
        older = series(1, CUTOFF - timedelta(hours=6), value=Decimal("500"))
        newer = series(2, CUTOFF - timedelta(minutes=30), value=Decimal("900"))
        outcome = choose_as_of(INTERVAL, CUTOFF, [older, newer])
        assert outcome.status == STATUS_SELECTED
        assert outcome.vintage_id == 2
        assert outcome.generation_mw == Decimal("900")

    def test_vintage_equal_to_cutoff_is_allowed(self) -> None:
        equal = series(1, CUTOFF)
        outcome = choose_as_of(INTERVAL, CUTOFF, [equal])
        assert outcome.vintage_id == 1
        assert outcome.publish_time_utc == CUTOFF

    def test_vintage_one_second_after_cutoff_is_never_selected(self) -> None:
        late = series(2, CUTOFF + timedelta(seconds=1))
        outcome = choose_as_of(INTERVAL, CUTOFF, [late])
        assert outcome.status == STATUS_NO_VINTAGE
        assert outcome.vintage_id is None
        assert outcome.generation_mw is None

    @pytest.mark.parametrize(
        "offset",
        [
            timedelta(seconds=1),
            timedelta(minutes=1),
            timedelta(hours=1),
            timedelta(hours=6),
            timedelta(days=1),
        ],
    )
    def test_any_publication_after_cutoff_is_excluded(self, offset: timedelta) -> None:
        eligible = series(1, CUTOFF - timedelta(hours=2), value=Decimal("100"))
        late = series(2, CUTOFF + offset, value=Decimal("999999"))
        outcome = choose_as_of(INTERVAL, CUTOFF, [eligible, late])
        assert outcome.vintage_id == 1
        assert outcome.generation_mw == Decimal("100")
        assert outcome.publish_time_utc <= CUTOFF

    def test_only_future_vintages_yields_missing(self) -> None:
        outcome = choose_as_of(
            INTERVAL, CUTOFF, [series(1, CUTOFF + timedelta(minutes=30))]
        )
        assert outcome.status == STATUS_NO_VINTAGE
        assert outcome.lead_time_minutes is None

    def test_no_vintages_at_all_yields_missing(self) -> None:
        outcome = choose_as_of(INTERVAL, CUTOFF, [])
        assert outcome.status == STATUS_NO_VINTAGE


class TestFallbackAndCoverage:
    def test_newest_vintage_missing_the_hour_falls_back(self) -> None:
        narrow = series(2, CUTOFF - timedelta(minutes=10), hours={INTERVAL + timedelta(days=2): Decimal("1")})
        broad = series(1, CUTOFF - timedelta(hours=8), value=Decimal("700"))
        outcome = choose_as_of(INTERVAL, CUTOFF, [narrow, broad])
        assert outcome.vintage_id == 1
        assert outcome.fallback_depth == 1
        assert outcome.generation_mw == Decimal("700")

    def test_no_vintage_covering_the_interval(self) -> None:
        elsewhere = series(
            1, CUTOFF - timedelta(hours=1), hours={INTERVAL + timedelta(days=5): Decimal("10")}
        )
        outcome = choose_as_of(INTERVAL, CUTOFF, [elsewhere])
        assert outcome.status == STATUS_NO_POINT
        assert outcome.vintage_id is None

    def test_null_forecast_is_selected_as_null_not_zero(self) -> None:
        nulls = series(1, CUTOFF - timedelta(hours=1), hours={INTERVAL: None})
        outcome = choose_as_of(INTERVAL, CUTOFF, [nulls])
        assert outcome.status == STATUS_SELECTED
        assert outcome.covers_interval is True
        assert outcome.generation_mw is None

    def test_vintage_published_after_the_interval_has_started_is_skipped(self) -> None:
        # Published 05:30 for an interval starting 06:00 is fine; 06:05 is not.
        too_late = series(2, INTERVAL + timedelta(minutes=5), value=Decimal("999"))
        usable = series(1, INTERVAL - timedelta(minutes=10), value=Decimal("321"))
        later_cutoff = INTERVAL + timedelta(hours=1)
        outcome = choose_as_of(INTERVAL, later_cutoff, [too_late, usable])
        assert outcome.vintage_id == 1
        assert outcome.generation_mw == Decimal("321")
        assert outcome.lead_time_minutes == 10
        assert outcome.fallback_depth == 1


class TestLeadTime:
    def test_lead_time_is_delivery_start_minus_publication(self) -> None:
        # A vintage 520 minutes before delivery. The cutoff here is deliberately
        # later than CUTOFF: with the 09:20 day-ahead cutoff this vintage would
        # (correctly) be ineligible, which is asserted separately below. This
        # test isolates the lead-time arithmetic from the eligibility rule.
        admitting_cutoff = datetime(2026, 1, 14, 23, 0, tzinfo=timezone.utc)
        outcome = choose_as_of(
            INTERVAL,
            admitting_cutoff,
            [series(1, datetime(2026, 1, 14, 21, 20, tzinfo=timezone.utc))],
        )
        assert outcome.status == STATUS_SELECTED
        assert outcome.lead_time_minutes == 520

    def test_lead_time_is_never_negative(self) -> None:
        outcome = choose_as_of(INTERVAL, CUTOFF, [])
        assert outcome.lead_time_minutes is None

    def test_vintage_published_after_the_cutoff_is_never_selected(self) -> None:
        # 21:20 is after the 09:20 day-ahead cutoff, so it is not eligible even
        # though it would otherwise be the freshest vintage for the interval.
        late = series(1, datetime(2026, 1, 14, 21, 20, tzinfo=timezone.utc))
        outcome = choose_as_of(INTERVAL, CUTOFF, [late])
        assert outcome.status == STATUS_NO_VINTAGE
        assert outcome.vintage_id is None
        assert outcome.lead_time_minutes is None


class TestIntervalMapping:
    def test_step_mapping_reuses_the_hour_value_for_both_periods(self) -> None:
        point_start = datetime(2026, 1, 15, 6, 0, tzinfo=timezone.utc)
        vintage = series(1, CUTOFF, hours={point_start: Decimal("400")})
        first = choose_as_of(INTERVAL, CUTOFF, [vintage], mapping="step")
        second = choose_as_of(
            INTERVAL + timedelta(minutes=30), CUTOFF, [vintage], mapping="step"
        )
        assert first.generation_mw == Decimal("400")
        assert second.generation_mw == Decimal("400")

    def test_half_hour_outside_any_hour_is_not_covered(self) -> None:
        covered, value = value_for_interval(
            series(1, CUTOFF, hours={datetime(2026, 1, 15, 9, tzinfo=timezone.utc): Decimal("1")}),
            INTERVAL,
        )
        assert covered is False
        assert value is None

    def test_linear_mapping_interpolates_at_the_midpoint(self) -> None:
        points = {
            datetime(2026, 1, 15, 6, tzinfo=timezone.utc): Decimal("100"),
            datetime(2026, 1, 15, 7, tzinfo=timezone.utc): Decimal("200"),
        }
        vintage = series(1, CUTOFF, hours=points)
        covered, value = value_for_interval(vintage, INTERVAL, mapping="linear")
        assert covered is True
        assert value == Decimal("150.0")

    def test_linear_mapping_falls_back_when_next_hour_is_missing(self) -> None:
        vintage = series(
            1,
            CUTOFF,
            hours={datetime(2026, 1, 15, 6, tzinfo=timezone.utc): Decimal("100")},
        )
        covered, value = value_for_interval(vintage, INTERVAL, mapping="linear")
        assert covered is True
        assert value == Decimal("100")

    def test_unknown_mapping_mode_is_rejected(self) -> None:
        vintage = series(1, CUTOFF)
        with pytest.raises(ValueError):
            value_for_interval(vintage, INTERVAL, mapping="cubic")  # type: ignore[arg-type]
