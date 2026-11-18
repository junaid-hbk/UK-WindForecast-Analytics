"""Data status, ingestion run and issue response models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.models.ingestion import IngestionRun
from app.models.quality import DataQualityIssue
from app.repositories.data_status_repository import CoverageDay
from app.services.data_status_service import DataStatus


class CoverageDayOut(BaseModel):
    """Per-delivery-day coverage."""

    settlement_date: date
    intervals: int
    selected_intervals: int
    missing_intervals: int
    earliest_used_vintage: datetime | None
    latest_used_vintage: datetime | None
    min_lead_minutes: int | None
    max_lead_minutes: int | None

    @classmethod
    def from_domain(cls, day: CoverageDay) -> "CoverageDayOut":
        return cls(**day.__dict__)


class IngestionRunOut(BaseModel):
    """One ingestion attempt."""

    run_id: int
    dataset: str
    run_type: str
    status: str
    window_from_utc: datetime
    window_to_utc: datetime
    rows_fetched: int
    rows_inserted: int
    rows_updated: int
    rows_rejected: int
    http_requests: int
    http_status: int | None
    error_code: str | None
    error_message: str | None
    started_at_utc: datetime
    finished_at_utc: datetime | None

    @classmethod
    def from_model(cls, run: IngestionRun) -> "IngestionRunOut":
        return cls(
            run_id=run.id,
            dataset=run.dataset,
            run_type=run.run_type,
            status=run.status,
            window_from_utc=run.window_from_utc,
            window_to_utc=run.window_to_utc,
            rows_fetched=run.rows_fetched,
            rows_inserted=run.rows_inserted,
            rows_updated=run.rows_updated,
            rows_rejected=run.rows_rejected,
            http_requests=run.http_requests,
            http_status=run.http_status,
            error_code=run.error_code,
            error_message=run.error_message,
            started_at_utc=run.started_at_utc,
            finished_at_utc=run.finished_at_utc,
        )


class IngestionSummaryOut(BaseModel):
    """Outcome of a synchronous ingestion request."""

    run_id: int
    dataset: str
    status: str
    window_from_utc: datetime
    window_to_utc: datetime
    rows_fetched: int
    rows_inserted: int
    rows_updated: int
    rows_rejected: int
    http_requests: int
    http_status: int | None
    vintages: int
    error_code: str | None
    error_message: str | None

    @classmethod
    def from_summary(cls, summary: object) -> "IngestionSummaryOut":
        payload = summary.to_dict()  # type: ignore[attr-defined]
        return cls(**payload)


class DataQualityIssueOut(BaseModel):
    """A recorded data problem."""

    issue_id: int
    dataset: str
    issue_type: str
    severity: str
    settlement_date: date | None
    settlement_period: int | None
    detail: str | None
    created_at_utc: datetime

    @classmethod
    def from_model(cls, issue: DataQualityIssue) -> "DataQualityIssueOut":
        return cls(
            issue_id=issue.id,
            dataset=issue.dataset,
            issue_type=issue.issue_type,
            severity=issue.severity,
            settlement_date=issue.settlement_date,
            settlement_period=issue.settlement_period,
            detail=issue.detail,
            created_at_utc=issue.created_at_utc,
        )


class DataStatusOut(BaseModel):
    """Aggregated data health."""

    policy_code: str
    date_from: date
    date_to: date
    stale: bool
    selection_intervals: int
    coverage_days_with_gaps: int
    latest_vintage_publish_time_utc: str | None
    latest_actual_settlement_date: date | None
    actual_rows: int
    actual_settlement_periods: int
    forecast_vintages: int
    forecast_points: int
    issue_counts: dict[str, int]
    coverage: list[CoverageDayOut]
    recent_runs: list[IngestionRunOut]
    notes: list[str]

    @classmethod
    def from_domain(cls, status: DataStatus) -> "DataStatusOut":
        return cls(
            policy_code=status.policy_code,
            date_from=status.date_from,
            date_to=status.date_to,
            stale=status.stale,
            selection_intervals=status.selection_intervals,
            coverage_days_with_gaps=status.coverage_days_with_gaps,
            latest_vintage_publish_time_utc=status.latest_vintage_publish_time_utc,
            latest_actual_settlement_date=status.latest_actual_settlement_date,
            actual_rows=status.actual_rows,
            actual_settlement_periods=status.actual_settlement_periods,
            forecast_vintages=status.forecast_vintages,
            forecast_points=status.forecast_points,
            issue_counts=status.issue_counts,
            coverage=[CoverageDayOut.from_domain(day) for day in status.coverage],
            recent_runs=[IngestionRunOut.from_model(run) for run in status.recent_runs],
            notes=status.notes,
        )
