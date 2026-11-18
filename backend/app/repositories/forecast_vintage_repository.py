"""Forecast vintage and point persistence.

Vintages are append-only. Re-ingesting the same publish window must not create a
second vintage, must not duplicate points, and must not lose a value that the
upstream provider republished under the same key: such a change is reported as a
revision so the ingestion service can record a data-quality issue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.integrations.elexon.forecasts import NormalisedVintage
from app.models.forecast import ForecastPoint, ForecastVintage
from app.repositories.base import BaseRepository

_CHUNK = 1000


@dataclass
class VintageUpsertResult:
    """Counts describing what a vintage write actually changed."""

    vintage_id: int
    created: bool
    points_inserted: int = 0
    points_updated: int = 0
    points_unchanged: int = 0
    revisions: list[tuple[datetime, Decimal | None, Decimal | None]] = field(default_factory=list)


@dataclass(frozen=True)
class SelectionInputs:
    """Everything the selection service needs, loaded in two queries."""

    vintages: dict[int, datetime]  # vintage_id -> publish_time_utc
    points: dict[int, dict[datetime, Decimal | None]]  # vintage_id -> {valid_from: value}


class ForecastVintageRepository(BaseRepository):
    """Persistence and bulk reads for WINDFOR vintages."""

    def get_by_publish_time(self, publish_time_utc: datetime) -> ForecastVintage | None:
        """Return the vintage published at exactly ``publish_time_utc``, if stored."""
        stmt = select(ForecastVintage).where(
            ForecastVintage.publish_time_utc == publish_time_utc
        )
        return self.session.scalars(stmt).one_or_none()

    def get_by_id(self, vintage_id: int) -> ForecastVintage | None:
        """Return a vintage by primary key."""
        return self.session.get(ForecastVintage, vintage_id)

    def list_for_publish_window(
        self, publish_from: datetime, publish_to: datetime
    ) -> list[ForecastVintage]:
        """Return vintages published in the half-open window, oldest first."""
        stmt = (
            select(ForecastVintage)
            .where(
                ForecastVintage.publish_time_utc >= publish_from,
                ForecastVintage.publish_time_utc < publish_to,
            )
            .order_by(ForecastVintage.publish_time_utc.asc())
        )
        return list(self.session.scalars(stmt))

    def count(self) -> int:
        """Total stored vintages (used by data status and tests)."""
        return int(self.session.scalar(select(func.count(ForecastVintage.id))) or 0)

    def upsert_vintage(self, vintage: NormalisedVintage, run_id: int | None) -> VintageUpsertResult:
        """Insert or refresh one vintage and its points. Does not commit."""
        existing = self.get_by_publish_time(vintage.publish_time_utc)
        created = existing is None
        if existing is None:
            record = ForecastVintage(
                dataset="WINDFOR",
                publish_time_utc=vintage.publish_time_utc,
                horizon_start_utc=vintage.horizon_start_utc,
                horizon_end_utc=vintage.horizon_end_utc,
                resolution_minutes=vintage.resolution_minutes,
                point_count=len(vintage.points),
                source_row_count=vintage.source_row_count,
                first_run_id=run_id,
                last_seen_run_id=run_id,
            )
            self.session.add(record)
            self.session.flush()
            vintage_id = record.id
        else:
            record = existing
            record.horizon_start_utc = min(record.horizon_start_utc, vintage.horizon_start_utc)
            record.horizon_end_utc = max(record.horizon_end_utc, vintage.horizon_end_utc)
            record.point_count = len(vintage.points)
            record.source_row_count = vintage.source_row_count
            record.last_seen_run_id = run_id
            vintage_id = record.id
            self.session.flush()

        result = VintageUpsertResult(vintage_id=vintage_id, created=created)
        existing_points = self._load_point_values(
            vintage_id, [p.valid_from_utc for p in vintage.points]
        )

        to_write: list[dict[str, object]] = []
        for point in vintage.points:
            if point.valid_from_utc in existing_points:
                previous = existing_points[point.valid_from_utc]
                if previous == point.generation_mw:
                    result.points_unchanged += 1
                    continue
                result.points_updated += 1
                result.revisions.append((point.valid_from_utc, previous, point.generation_mw))
                to_write.append(
                    {
                        "vintage_id": vintage_id,
                        "valid_from_utc": point.valid_from_utc,
                        "valid_to_utc": point.valid_to_utc,
                        "generation_mw": point.generation_mw,
                    }
                )
                continue
            result.points_inserted += 1
            to_write.append(
                {
                    "vintage_id": vintage_id,
                    "valid_from_utc": point.valid_from_utc,
                    "valid_to_utc": point.valid_to_utc,
                    "generation_mw": point.generation_mw,
                }
            )

        for start in range(0, len(to_write), _CHUNK):
            chunk = to_write[start : start + _CHUNK]
            stmt = mysql_insert(ForecastPoint).values(chunk)
            stmt = stmt.on_duplicate_key_update(
                generation_mw=stmt.inserted.generation_mw,
                valid_to_utc=stmt.inserted.valid_to_utc,
            )
            self.session.execute(stmt)

        return result

    def _load_point_values(
        self, vintage_id: int, valid_from_values: list[datetime]
    ) -> dict[datetime, Decimal | None]:
        if not valid_from_values:
            return {}
        stmt = select(ForecastPoint.valid_from_utc, ForecastPoint.generation_mw).where(
            ForecastPoint.vintage_id == vintage_id,
            ForecastPoint.valid_from_utc.in_(valid_from_values),
        )
        return {row[0]: row[1] for row in self.session.execute(stmt)}

    def load_points(self, vintage_id: int) -> list[ForecastPoint]:
        """Return every point of a vintage ordered by validity start."""
        stmt = (
            select(ForecastPoint)
            .where(ForecastPoint.vintage_id == vintage_id)
            .order_by(ForecastPoint.valid_from_utc.asc())
        )
        return list(self.session.scalars(stmt))

    def load_selection_inputs(
        self,
        *,
        earliest_bucket_utc: datetime,
        latest_bucket_utc: datetime,
        cutoff_ceiling_utc: datetime,
    ) -> SelectionInputs:
        """Load vintages eligible at or before the ceiling and their points.

        Two queries only, so a two-month rebuild does not issue per-interval SQL.
        """
        vintage_stmt = (
            select(ForecastVintage.id, ForecastVintage.publish_time_utc)
            .where(
                ForecastVintage.publish_time_utc <= cutoff_ceiling_utc,
                ForecastVintage.horizon_end_utc > earliest_bucket_utc,
                ForecastVintage.horizon_start_utc <= latest_bucket_utc,
            )
            .order_by(ForecastVintage.publish_time_utc.desc(), ForecastVintage.id.desc())
        )
        vintage_rows = list(self.session.execute(vintage_stmt))
        vintages = {row[0]: row[1] for row in vintage_rows}
        if not vintages:
            return SelectionInputs(vintages={}, points={})

        point_stmt = select(
            ForecastPoint.vintage_id,
            ForecastPoint.valid_from_utc,
            ForecastPoint.generation_mw,
        ).where(
            ForecastPoint.vintage_id.in_(list(vintages)),
            ForecastPoint.valid_from_utc >= earliest_bucket_utc,
            ForecastPoint.valid_from_utc <= latest_bucket_utc,
        )
        points: dict[int, dict[datetime, Decimal | None]] = {vid: {} for vid in vintages}
        for vintage_id, valid_from, generation in self.session.execute(point_stmt):
            points[vintage_id][valid_from] = generation
        return SelectionInputs(vintages=vintages, points=points)
