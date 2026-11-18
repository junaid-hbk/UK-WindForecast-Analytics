"""Actual generation persistence.

Each upstream publication of a settlement period is a separate row (a revision),
so outturn changes remain auditable. The unique constraint makes re-ingestion a
no-op instead of a duplicate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.integrations.elexon.actuals import NormalisedActual
from app.models.actual import ActualGeneration
from app.models.views import actual_generation_latest as v_actual_latest
from app.repositories.base import BaseRepository

_CHUNK = 1000


@dataclass
class ActualUpsertResult:
    """Counts describing what an actuals write actually changed."""

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass(frozen=True)
class ActualPoint:
    """A latest-revision actual value for one settlement period."""

    settlement_date: date
    settlement_period: int
    start_time_utc: datetime
    generation_mw: Decimal | None
    source_publish_time_utc: datetime


class ActualGenerationRepository(BaseRepository):
    """Persistence and reads for FUELHH wind outturn."""

    def upsert_many(
        self, rows: list[NormalisedActual], run_id: int | None
    ) -> ActualUpsertResult:
        """Insert new revisions; leave identical rows untouched. Does not commit."""
        result = ActualUpsertResult()
        if not rows:
            return result

        existing = self._load_existing(rows)
        to_write: list[dict[str, object]] = []
        for row in rows:
            key = (row.settlement_date, row.settlement_period, row.publish_time_utc)
            if key in existing:
                previous = existing[key]
                if previous == row.generation_mw:
                    result.unchanged += 1
                    continue
                result.updated += 1
            else:
                result.inserted += 1
            to_write.append(
                {
                    "settlement_date": row.settlement_date,
                    "settlement_period": row.settlement_period,
                    "fuel_type": "WIND",
                    "start_time_utc": row.start_time_utc,
                    "end_time_utc": row.end_time_utc,
                    "generation_mw": row.generation_mw,
                    "source_publish_time_utc": row.publish_time_utc,
                    "ingestion_run_id": run_id,
                }
            )

        for start in range(0, len(to_write), _CHUNK):
            chunk = to_write[start : start + _CHUNK]
            stmt = mysql_insert(ActualGeneration).values(chunk)
            stmt = stmt.on_duplicate_key_update(
                generation_mw=stmt.inserted.generation_mw,
                ingestion_run_id=stmt.inserted.ingestion_run_id,
            )
            self.session.execute(stmt)
        return result

    def _load_existing(
        self, rows: list[NormalisedActual]
    ) -> dict[tuple[date, int, datetime], Decimal | None]:
        dates = {row.settlement_date for row in rows}
        stmt = select(
            ActualGeneration.settlement_date,
            ActualGeneration.settlement_period,
            ActualGeneration.source_publish_time_utc,
            ActualGeneration.generation_mw,
        ).where(
            ActualGeneration.fuel_type == "WIND",
            ActualGeneration.settlement_date.in_(dates),
        )
        return {
            (row[0], row[1], row[2]): row[3] for row in self.session.execute(stmt)
        }

    def latest_for_range(self, date_from: date, date_to: date) -> list[ActualPoint]:
        """Return the latest revision per settlement period via the sanctioned view."""
        stmt = (
            select(
                v_actual_latest.c.settlement_date,
                v_actual_latest.c.settlement_period,
                v_actual_latest.c.start_time_utc,
                v_actual_latest.c.generation_mw,
                v_actual_latest.c.source_publish_time_utc,
            )
            .where(
                v_actual_latest.c.fuel_type == "WIND",
                v_actual_latest.c.settlement_date >= date_from,
                v_actual_latest.c.settlement_date <= date_to,
            )
            .order_by(
                v_actual_latest.c.settlement_date.asc(),
                v_actual_latest.c.settlement_period.asc(),
            )
        )
        return [
            ActualPoint(
                settlement_date=row.settlement_date,
                settlement_period=row.settlement_period,
                start_time_utc=row.start_time_utc,
                generation_mw=row.generation_mw,
                source_publish_time_utc=row.source_publish_time_utc,
            )
            for row in self.session.execute(stmt)
        ]

    def count_latest_for_range(self, date_from: date, date_to: date) -> int:
        """Number of settlement periods with at least one stored actual."""
        stmt = (
            select(func.count())
            .select_from(v_actual_latest)
            .where(
                v_actual_latest.c.fuel_type == "WIND",
                v_actual_latest.c.settlement_date >= date_from,
                v_actual_latest.c.settlement_date <= date_to,
            )
        )
        return int(self.session.execute(stmt).scalar() or 0)

    def revision_count(self) -> int:
        """Total stored actual rows (revisions included)."""
        return int(self.session.scalar(select(func.count(ActualGeneration.id))) or 0)
