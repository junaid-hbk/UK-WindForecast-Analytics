"""Data-quality issue persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select

from app.models.quality import DataQualityIssue
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class QualityIssue:
    """An issue to record."""

    dataset: str
    issue_type: str
    severity: str
    detail: str | None = None
    settlement_date: date | None = None
    settlement_period: int | None = None
    vintage_publish_time_utc: datetime | None = None


class DataQualityRepository(BaseRepository):
    """Append-only issue log."""

    def add_many(self, issues: list[QualityIssue], *, run_id: int | None = None) -> int:
        """Insert issues; returns how many were written."""
        if not issues:
            return 0
        self.session.add_all(
            [
                DataQualityIssue(
                    ingestion_run_id=run_id,
                    dataset=issue.dataset,
                    issue_type=issue.issue_type,
                    severity=issue.severity,
                    settlement_date=issue.settlement_date,
                    settlement_period=issue.settlement_period,
                    vintage_publish_time_utc=issue.vintage_publish_time_utc,
                    detail=(issue.detail or "")[:1000] or None,
                )
                for issue in issues
            ]
        )
        return len(issues)

    def recent(self, *, limit: int = 100, severity: str | None = None) -> list[DataQualityIssue]:
        """Newest issues first, optionally filtered by severity."""
        stmt = select(DataQualityIssue).order_by(DataQualityIssue.id.desc())
        if severity is not None:
            stmt = stmt.where(DataQualityIssue.severity == severity)
        return list(self.session.scalars(stmt.limit(limit)))

    def counts_by_type(self) -> dict[str, int]:
        """Issue counts grouped by type."""
        stmt = select(DataQualityIssue.issue_type, func.count(DataQualityIssue.id)).group_by(
            DataQualityIssue.issue_type
        )
        return {row[0]: int(row[1]) for row in self.session.execute(stmt)}
