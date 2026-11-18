"""Chunking helpers for bounded external requests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timedelta


def date_chunks(start: date, end: date, chunk_days: int) -> Iterator[tuple[date, date]]:
    """Yield inclusive ``(from, to)`` date chunks covering ``[start, end]``.

    Raises ``ValueError`` for an inverted range or a non-positive chunk size
    rather than silently returning nothing.
    """
    if chunk_days < 1:
        raise ValueError("chunk_days must be >= 1")
    if end < start:
        raise ValueError(f"end date {end} precedes start date {start}")
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def datetime_chunks(
    start: datetime, end: datetime, chunk_days: int
) -> Iterator[tuple[datetime, datetime]]:
    """Yield half-open ``[from, to)`` datetime chunks covering ``[start, end)``."""
    if chunk_days < 1:
        raise ValueError("chunk_days must be >= 1")
    if end <= start:
        raise ValueError(f"end {end} must be after start {start}")
    step = timedelta(days=chunk_days)
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + step, end)
        yield cursor, chunk_end
        cursor = chunk_end
