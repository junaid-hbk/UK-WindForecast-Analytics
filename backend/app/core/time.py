"""Time and GB settlement-period handling.

This module is the single source of truth for time arithmetic in the project:

* all instants are stored and reasoned about in **UTC**;
* the GB settlement day is a **Europe/London** calendar day, which is 23, 24 or
  25 hours long on daylight-saving transition days (46, 48 or 50 settlement
  periods respectively);
* settlement-period boundaries are contiguous UTC instants measured from local
  midnight, so a 25-hour day simply has two extra periods.

Nothing here uses fixed UTC offsets; every conversion goes through
``zoneinfo.ZoneInfo("Europe/London")``.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

LONDON_TZ = ZoneInfo("Europe/London")
UTC = timezone.utc
SETTLEMENT_PERIOD_MINUTES = 30
_SETTLEMENT_PERIOD = timedelta(minutes=SETTLEMENT_PERIOD_MINUTES)


def ensure_utc(value: datetime) -> datetime:
    """Return an aware UTC datetime.

    Naive datetimes are interpreted as UTC (our storage convention), never as
    local time, because silently re-interpreting them would shift data by an
    hour across a DST boundary.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_london(value: datetime) -> datetime:
    """Convert an instant to Europe/London wall-clock time."""
    return ensure_utc(value).astimezone(LONDON_TZ)


def utc_now() -> datetime:
    """Current instant, aware, UTC, microsecond precision truncated to seconds."""
    return datetime.now(tz=UTC).replace(microsecond=0)


def settlement_day_start_utc(day: date) -> datetime:
    """UTC instant of local midnight at the start of a GB settlement day."""
    local_midnight = datetime.combine(day, time(0, 0), tzinfo=LONDON_TZ)
    return local_midnight.astimezone(UTC)


def settlement_day_end_utc(day: date) -> datetime:
    """UTC instant of local midnight at the end of a GB settlement day (exclusive)."""
    return settlement_day_start_utc(day + timedelta(days=1))


def settlement_periods_in_day(day: date) -> int:
    """Number of 30-minute settlement periods in a settlement day (46/48/50)."""
    span = settlement_day_end_utc(day) - settlement_day_start_utc(day)
    return int(span.total_seconds() // (SETTLEMENT_PERIOD_MINUTES * 60))


def interval_for_period(day: date, period: int) -> tuple[datetime, datetime]:
    """Return the half-open UTC interval ``[start, end)`` for a settlement period."""
    total = settlement_periods_in_day(day)
    if not 1 <= period <= total:
        raise ValueError(
            f"settlement period {period} is out of range for {day.isoformat()} (1..{total})"
        )
    start = settlement_day_start_utc(day) + _SETTLEMENT_PERIOD * (period - 1)
    return start, start + _SETTLEMENT_PERIOD


def period_for_instant(instant: datetime) -> tuple[date, int]:
    """Map a UTC instant to its GB settlement date and period."""
    utc_value = ensure_utc(instant)
    settlement_date = to_london(utc_value).date()
    start = settlement_day_start_utc(settlement_date)
    elapsed = utc_value - start
    period = int(elapsed.total_seconds() // (SETTLEMENT_PERIOD_MINUTES * 60)) + 1
    return settlement_date, period


def resolve_cutoff(
    delivery_date: date,
    local_time: time,
    *,
    offset_days: int = -1,
    tz: ZoneInfo = LONDON_TZ,
) -> datetime:
    """Resolve a wall-clock decision cutoff to a UTC instant.

    ``local_time`` is interpreted in ``tz`` on ``delivery_date + offset_days``.
    Ambiguous wall-clock times (the repeated hour when clocks go back) resolve to
    the *first* occurrence (``fold=0``), which is the conservative choice: it
    cannot admit a forecast published later. Nonexistent times (spring forward)
    resolve forward per ``fold`` semantics; a 09:20 cutoff is never affected.
    """
    local_date = delivery_date + timedelta(days=offset_days)
    naive = datetime.combine(local_date, local_time)
    aware = naive.replace(tzinfo=tz, fold=0)
    return aware.astimezone(UTC)


def floor_to_hour(instant: datetime) -> datetime:
    """Floor an instant to the start of its UTC hour."""
    value = ensure_utc(instant)
    return value.replace(minute=0, second=0, microsecond=0)


def ceil_to_hour(instant: datetime) -> datetime:
    """Ceiling an instant to the start of the next UTC hour."""
    floored = floor_to_hour(instant)
    return floored if floored == ensure_utc(instant) else floored + timedelta(hours=1)


def format_utc(instant: datetime) -> str:
    """ISO-8601 UTC representation used in API payloads."""
    return ensure_utc(instant).isoformat().replace("+00:00", "Z")
