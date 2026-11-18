"""Materialised forecast selection persistence and the analysis read query."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete, select, text

from app.models.selection import ForecastSelection
from app.models.views import analysis_interval as v_analysis_interval
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class SelectionRow:
    """A selection outcome ready for persistence."""

    settlement_date: date
    settlement_period: int
    interval_start_utc: datetime
    cutoff_utc: datetime
    vintage_id: int | None
    vintage_publish_time_utc: datetime | None
    lead_time_minutes: int | None
    forecast_mw: Decimal | None
    fallback_depth: int
    selection_status: str


@dataclass(frozen=True)
class AnalysisInterval:
    """One analysed interval: as-of forecast joined to the latest actual."""

    settlement_date: date
    settlement_period: int
    interval_start_utc: datetime
    cutoff_utc: datetime
    vintage_publish_time_utc: datetime | None
    lead_time_minutes: int | None
    forecast_mw: Decimal | None
    actual_mw: Decimal | None
    selection_status: str


class ForecastSelectionRepository(BaseRepository):
    """Rebuild and read the materialised as-of selection."""

    def replace_range(
        self,
        *,
        policy_id: int,
        date_from: date,
        date_to: date,
        rows: list[SelectionRow],
    ) -> int:
        """Replace all selections for a policy and date range. Does not commit."""
        self.session.execute(
            delete(ForecastSelection).where(
                ForecastSelection.cutoff_policy_id == policy_id,
                ForecastSelection.settlement_date >= date_from,
                ForecastSelection.settlement_date <= date_to,
            )
        )
        if not rows:
            return 0
        payload = [
            {
                "cutoff_policy_id": policy_id,
                "settlement_date": row.settlement_date,
                "settlement_period": row.settlement_period,
                "interval_start_utc": row.interval_start_utc,
                "cutoff_utc": row.cutoff_utc,
                "vintage_id": row.vintage_id,
                "vintage_publish_time_utc": row.vintage_publish_time_utc,
                "lead_time_minutes": row.lead_time_minutes,
                "forecast_mw": row.forecast_mw,
                "fallback_depth": row.fallback_depth,
                "selection_status": row.selection_status,
            }
            for row in rows
        ]
        self.session.execute(ForecastSelection.__table__.insert(), payload)
        return len(payload)

    def count_range(self, policy_id: int, date_from: date, date_to: date) -> int:
        """Number of selection rows stored for a policy and range."""
        stmt = text(
            """
            SELECT COUNT(*) FROM forecast_selection
            WHERE cutoff_policy_id = :policy_id
              AND settlement_date BETWEEN :date_from AND :date_to
            """
        )
        return int(
            self.session.execute(
                stmt,
                {"policy_id": policy_id, "date_from": date_from, "date_to": date_to},
            ).scalar()
            or 0
        )

    def fetch_analysis_intervals(
        self, *, policy_id: int, date_from: date, date_to: date
    ) -> list[AnalysisInterval]:
        """Read the analysed intervals from the sanctioned analysis view."""
        stmt = (
            select(
                v_analysis_interval.c.settlement_date,
                v_analysis_interval.c.settlement_period,
                v_analysis_interval.c.interval_start_utc,
                v_analysis_interval.c.cutoff_utc,
                v_analysis_interval.c.vintage_publish_time_utc,
                v_analysis_interval.c.lead_time_minutes,
                v_analysis_interval.c.forecast_mw,
                v_analysis_interval.c.actual_mw,
                v_analysis_interval.c.selection_status,
            )
            .where(
                v_analysis_interval.c.cutoff_policy_id == policy_id,
                v_analysis_interval.c.settlement_date >= date_from,
                v_analysis_interval.c.settlement_date <= date_to,
            )
            .order_by(
                v_analysis_interval.c.settlement_date.asc(),
                v_analysis_interval.c.settlement_period.asc(),
            )
        )
        return [
            AnalysisInterval(
                settlement_date=row.settlement_date,
                settlement_period=row.settlement_period,
                interval_start_utc=row.interval_start_utc,
                cutoff_utc=row.cutoff_utc,
                vintage_publish_time_utc=row.vintage_publish_time_utc,
                lead_time_minutes=row.lead_time_minutes,
                forecast_mw=row.forecast_mw,
                actual_mw=row.actual_mw,
                selection_status=row.selection_status,
            )
            for row in self.session.execute(stmt)
        ]

    def fetch_day_selections(self, *, policy_id: int, delivery_date: date) -> list[SelectionRow]:
        """Return the stored selection rows for one delivery day."""
        stmt = (
            select(ForecastSelection)
            .where(
                ForecastSelection.cutoff_policy_id == policy_id,
                ForecastSelection.settlement_date == delivery_date,
            )
            .order_by(ForecastSelection.settlement_period.asc())
        )
        return [
            SelectionRow(
                settlement_date=record.settlement_date,
                settlement_period=record.settlement_period,
                interval_start_utc=record.interval_start_utc,
                cutoff_utc=record.cutoff_utc,
                vintage_id=record.vintage_id,
                vintage_publish_time_utc=record.vintage_publish_time_utc,
                lead_time_minutes=record.lead_time_minutes,
                forecast_mw=record.forecast_mw,
                fallback_depth=record.fallback_depth,
                selection_status=record.selection_status,
            )
            for record in self.session.scalars(stmt)
        ]
