"""Data status: coverage, freshness, ingestion history and issue counts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.core import time as time_utils
from app.models.ingestion import IngestionRun
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.data_quality_repository import DataQualityRepository
from app.repositories.data_status_repository import CoverageDay, DataStatusRepository
from app.repositories.forecast_selection_repository import ForecastSelectionRepository
from app.repositories.ingestion_run_repository import IngestionRunRepository


@dataclass
class DataStatus:
    """Everything an operator needs to judge whether the data is trustworthy."""

    policy_code: str
    date_from: date
    date_to: date
    coverage: list[CoverageDay] = field(default_factory=list)
    coverage_days_with_gaps: int = 0
    selection_intervals: int = 0
    latest_vintage_publish_time_utc: str | None = None
    latest_actual_settlement_date: date | None = None
    actual_rows: int = 0
    actual_settlement_periods: int = 0
    forecast_vintages: int = 0
    forecast_points: int = 0
    issue_counts: dict[str, int] = field(default_factory=dict)
    recent_runs: list[IngestionRun] = field(default_factory=list)
    stale: bool = False
    notes: list[str] = field(default_factory=list)


class DataStatusService:
    """Read-only aggregation of data health."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_status(
        self,
        *,
        date_from: date,
        date_to: date,
        policy_code: str | None = None,
        run_limit: int = 10,
    ) -> DataStatus:
        """Assemble the status payload."""
        policy = CutoffPolicyRepository(self._session).resolve(policy_code)
        status_repo = DataStatusRepository(self._session)

        coverage = status_repo.coverage(policy.id, date_from, date_to)
        selection_intervals = ForecastSelectionRepository(self._session).count_range(
            policy.id, date_from, date_to
        )
        latest_vintage = status_repo.latest_vintage()
        latest_actual = status_repo.latest_actual_date()
        actuals = status_repo.actual_counts()
        forecasts = status_repo.forecast_counts()

        status = DataStatus(
            policy_code=policy.code,
            date_from=date_from,
            date_to=date_to,
            coverage=coverage,
            coverage_days_with_gaps=sum(1 for day in coverage if day.missing_intervals > 0),
            selection_intervals=selection_intervals,
            latest_vintage_publish_time_utc=(
                time_utils.format_utc(latest_vintage.publish_time_utc) if latest_vintage else None
            ),
            latest_actual_settlement_date=latest_actual,
            actual_rows=actuals["rows"],
            actual_settlement_periods=actuals["settlement_periods"],
            forecast_vintages=forecasts["vintages"],
            forecast_points=forecasts["points"],
            issue_counts=DataQualityRepository(self._session).counts_by_type(),
            recent_runs=IngestionRunRepository(self._session).recent(limit=run_limit),
        )

        if latest_actual is None:
            status.stale = True
            status.notes.append("No actual generation has been ingested.")
        else:
            age_days = (time_utils.to_london(time_utils.utc_now()).date() - latest_actual).days
            status.stale = age_days > 2
            status.notes.append(f"Latest actual settlement date is {latest_actual.isoformat()}.")

        if latest_vintage is None:
            status.stale = True
            status.notes.append("No forecast vintages have been ingested.")

        if coverage and status.coverage_days_with_gaps:
            status.notes.append(
                f"{status.coverage_days_with_gaps} delivery day(s) in range have intervals "
                "without a decision-ready forecast."
            )

        return status
