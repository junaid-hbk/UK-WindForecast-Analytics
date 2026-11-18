"""Data-status reads (coverage, freshness, counts)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select

from app.models.actual import ActualGeneration
from app.models.forecast import ForecastPoint, ForecastVintage
from app.models.views import forecast_coverage_daily as v_coverage
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class CoverageDay:
    """Per-delivery-day forecast selection coverage."""

    settlement_date: date
    intervals: int
    selected_intervals: int
    missing_intervals: int
    earliest_used_vintage: datetime | None
    latest_used_vintage: datetime | None
    min_lead_minutes: int | None
    max_lead_minutes: int | None


class DataStatusRepository(BaseRepository):
    """Read-only status queries used by the ops page and diagnostics."""

    def coverage(self, policy_id: int, date_from: date, date_to: date) -> list[CoverageDay]:
        """Read the coverage view for a policy and range."""
        stmt = (
            select(
                v_coverage.c.settlement_date,
                v_coverage.c.intervals,
                v_coverage.c.selected_intervals,
                v_coverage.c.missing_intervals,
                v_coverage.c.earliest_used_vintage,
                v_coverage.c.latest_used_vintage,
                v_coverage.c.min_lead_minutes,
                v_coverage.c.max_lead_minutes,
            )
            .where(
                v_coverage.c.cutoff_policy_id == policy_id,
                v_coverage.c.settlement_date >= date_from,
                v_coverage.c.settlement_date <= date_to,
            )
            .order_by(v_coverage.c.settlement_date.asc())
        )
        return [
            CoverageDay(
                settlement_date=row.settlement_date,
                intervals=int(row.intervals or 0),
                selected_intervals=int(row.selected_intervals or 0),
                missing_intervals=int(row.missing_intervals or 0),
                earliest_used_vintage=row.earliest_used_vintage,
                latest_used_vintage=row.latest_used_vintage,
                min_lead_minutes=row.min_lead_minutes,
                max_lead_minutes=row.max_lead_minutes,
            )
            for row in self.session.execute(stmt)
        ]

    def latest_vintage(self) -> ForecastVintage | None:
        """Most recently published stored vintage."""
        stmt = select(ForecastVintage).order_by(ForecastVintage.publish_time_utc.desc()).limit(1)
        return self.session.scalars(stmt).first()

    def latest_actual_date(self) -> date | None:
        """Latest settlement date with stored actual generation."""
        return self.session.scalar(
            select(func.max(ActualGeneration.settlement_date)).where(
                ActualGeneration.fuel_type == "WIND"
            )
        )

    def actual_counts(self) -> dict[str, int]:
        """Row and distinct-period counts for actual generation."""
        total = int(self.session.scalar(select(func.count(ActualGeneration.id))) or 0)
        distinct = int(
            self.session.scalar(
                select(
                    func.count(
                        func.distinct(
                            func.concat(
                                ActualGeneration.settlement_date,
                                ":",
                                ActualGeneration.settlement_period,
                            )
                        )
                    )
                ).where(ActualGeneration.fuel_type == "WIND")
            )
            or 0
        )
        return {"rows": total, "settlement_periods": distinct}

    def forecast_counts(self) -> dict[str, int]:
        """Vintage and point counts."""
        vintages = int(self.session.scalar(select(func.count(ForecastVintage.id))) or 0)
        points = int(self.session.scalar(select(func.count()).select_from(ForecastPoint)) or 0)
        return {"vintages": vintages, "points": points}
