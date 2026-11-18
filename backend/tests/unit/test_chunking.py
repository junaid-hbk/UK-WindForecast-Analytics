"""Chunking helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.utils.chunking import date_chunks, datetime_chunks


class TestDateChunks:
    def test_single_chunk_when_range_fits(self) -> None:
        chunks = list(date_chunks(date(2026, 1, 1), date(2026, 1, 3), 7))
        assert chunks == [(date(2026, 1, 1), date(2026, 1, 3))]

    def test_inclusive_windows_without_gaps_or_overlap(self) -> None:
        chunks = list(date_chunks(date(2026, 1, 1), date(2026, 1, 31), 7))
        assert chunks[0][0] == date(2026, 1, 1)
        assert chunks[-1][1] == date(2026, 1, 31)
        for previous, current in zip(chunks, chunks[1:]):
            assert current[0] == previous[1] + timedelta(days=1)

    def test_inverted_range_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            list(date_chunks(date(2026, 1, 5), date(2026, 1, 1), 7))

    def test_zero_chunk_days_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            list(date_chunks(date(2026, 1, 1), date(2026, 1, 2), 0))


class TestDatetimeChunks:
    def test_half_open_windows_are_contiguous(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 4, tzinfo=timezone.utc)
        chunks = list(datetime_chunks(start, end, 1))
        assert len(chunks) == 3
        assert chunks[0][0] == start
        assert chunks[-1][1] == end
        for previous, current in zip(chunks, chunks[1:]):
            assert current[0] == previous[1]

    def test_partial_final_chunk(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(hours=30)
        chunks = list(datetime_chunks(start, end, 1))
        assert chunks[-1][1] == end
        assert chunks[-1][1] - chunks[-1][0] == timedelta(hours=6)

    def test_empty_range_is_rejected(self) -> None:
        moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            list(datetime_chunks(moment, moment, 1))
