"""Time and settlement-period tests, including daylight-saving transitions.

UK clock changes in 2026: forward on Sunday 29 March (23-hour day, 46 periods)
and back on Sunday 25 October (25-hour day, 50 periods).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.core import time as time_utils

LONDON = ZoneInfo("Europe/London")


class TestSettlementCalendar:
    def test_normal_gmt_day_has_48_periods(self) -> None:
        assert time_utils.settlement_periods_in_day(date(2026, 1, 15)) == 48

    def test_spring_forward_day_has_46_periods(self) -> None:
        assert time_utils.settlement_periods_in_day(date(2026, 3, 29)) == 46

    def test_autumn_back_day_has_50_periods(self) -> None:
        assert time_utils.settlement_periods_in_day(date(2026, 10, 25)) == 50

    def test_winter_day_starts_at_midnight_utc(self) -> None:
        assert time_utils.settlement_day_start_utc(date(2026, 1, 15)) == datetime(
            2026, 1, 15, tzinfo=timezone.utc
        )

    def test_summer_day_starts_an_hour_earlier_in_utc(self) -> None:
        assert time_utils.settlement_day_start_utc(date(2026, 7, 1)) == datetime(
            2026, 6, 30, 23, tzinfo=timezone.utc
        )

    def test_first_period_of_winter_day(self) -> None:
        start, end = time_utils.interval_for_period(date(2026, 1, 15), 1)
        assert start == datetime(2026, 1, 15, tzinfo=timezone.utc)
        assert end - start == timedelta(minutes=30)

    def test_first_period_of_summer_day(self) -> None:
        start, _ = time_utils.interval_for_period(date(2026, 7, 1), 1)
        assert start == datetime(2026, 6, 30, 23, tzinfo=timezone.utc)

    def test_spring_forward_day_has_no_period_47(self) -> None:
        with pytest.raises(ValueError):
            time_utils.interval_for_period(date(2026, 3, 29), 47)

    def test_period_zero_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            time_utils.interval_for_period(date(2026, 1, 15), 0)

    def test_autumn_day_has_a_period_50(self) -> None:
        start, end = time_utils.interval_for_period(date(2026, 10, 25), 50)
        assert end == time_utils.settlement_day_end_utc(date(2026, 10, 25))
        assert end - start == timedelta(minutes=30)

    def test_intervals_are_contiguous_across_the_autumn_transition(self) -> None:
        day = date(2026, 10, 25)
        previous_end = time_utils.settlement_day_start_utc(day)
        for period in range(1, 51):
            start, end = time_utils.interval_for_period(day, period)
            assert start == previous_end
            previous_end = end


class TestPeriodForInstant:
    @pytest.mark.parametrize("period", [1, 2, 24, 47, 48])
    def test_round_trip_on_a_normal_day(self, period: int) -> None:
        day = date(2026, 1, 15)
        start, _ = time_utils.interval_for_period(day, period)
        assert time_utils.period_for_instant(start) == (day, period)

    def test_repeated_hour_periods_are_distinct(self) -> None:
        # 00:30Z is 01:30 BST; 01:00Z is 01:00 GMT after the clocks go back.
        assert time_utils.period_for_instant(datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)) == (
            date(2026, 10, 25),
            4,
        )
        assert time_utils.period_for_instant(datetime(2026, 10, 25, 1, 0, tzinfo=timezone.utc)) == (
            date(2026, 10, 25),
            5,
        )

    def test_local_midnight_maps_to_period_one(self) -> None:
        local_midnight = datetime(2026, 7, 1, 0, 0, tzinfo=LONDON)
        assert time_utils.period_for_instant(local_midnight) == (date(2026, 7, 1), 1)


class TestCutoffResolution:
    def test_winter_cutoff_is_utc_wall_clock(self) -> None:
        cutoff = time_utils.resolve_cutoff(date(2026, 1, 15), time(9, 20))
        assert cutoff == datetime(2026, 1, 14, 9, 20, tzinfo=timezone.utc)

    def test_summer_cutoff_is_one_hour_earlier_in_utc(self) -> None:
        cutoff = time_utils.resolve_cutoff(date(2026, 7, 1), time(9, 20))
        assert cutoff == datetime(2026, 6, 30, 8, 20, tzinfo=timezone.utc)

    def test_cutoff_on_the_eve_of_the_spring_transition(self) -> None:
        # Delivery 2026-03-29; cutoff falls on 2026-03-28, still GMT.
        cutoff = time_utils.resolve_cutoff(date(2026, 3, 29), time(9, 20))
        assert cutoff == datetime(2026, 3, 28, 9, 20, tzinfo=timezone.utc)

    def test_cutoff_after_the_spring_transition(self) -> None:
        cutoff = time_utils.resolve_cutoff(date(2026, 3, 30), time(9, 20))
        assert cutoff == datetime(2026, 3, 29, 8, 20, tzinfo=timezone.utc)

    def test_same_day_cutoff_policy(self) -> None:
        cutoff = time_utils.resolve_cutoff(date(2026, 1, 15), time(15, 30), offset_days=0)
        assert cutoff == datetime(2026, 1, 15, 15, 30, tzinfo=timezone.utc)

    def test_cutoff_is_strictly_before_delivery_day(self) -> None:
        cutoff = time_utils.resolve_cutoff(date(2026, 1, 15), time(9, 20))
        assert cutoff < time_utils.settlement_day_start_utc(date(2026, 1, 15))


class TestHelpers:
    def test_naive_datetimes_are_treated_as_utc(self) -> None:
        assert time_utils.ensure_utc(datetime(2026, 1, 15, 12, 0)) == datetime(
            2026, 1, 15, 12, 0, tzinfo=timezone.utc
        )

    def test_london_conversion_in_summer(self) -> None:
        local = time_utils.to_london(datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc))
        assert local.hour == 13
        assert local.tzname() == "BST"

    def test_london_conversion_in_winter(self) -> None:
        local = time_utils.to_london(datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc))
        assert local.hour == 12
        assert local.tzname() == "GMT"

    def test_floor_and_ceil_to_hour(self) -> None:
        moment = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)
        assert time_utils.floor_to_hour(moment) == datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
        assert time_utils.ceil_to_hour(moment) == datetime(2026, 1, 15, 13, tzinfo=timezone.utc)
        exact = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
        assert time_utils.ceil_to_hour(exact) == exact

    def test_format_utc_uses_z_suffix(self) -> None:
        assert time_utils.format_utc(datetime(2026, 1, 15, 12, tzinfo=timezone.utc)) == (
            "2026-01-15T12:00:00Z"
        )
