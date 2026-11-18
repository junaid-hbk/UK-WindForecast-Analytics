"""Ingestion orchestration.

Guarantees:

* **Run bookkeeping is separate from data.** A run row is committed before any
  fetch, so a crash leaves evidence; data is committed only after every chunk has
  been validated, so a mid-run upstream failure never leaves a partial vintage
  set and never touches previously ingested data.
* **A failure is reported, not swallowed.** The run is marked ``failed`` with the
  actual error code/message, and the exception propagates so the CLI exits
  non-zero and the admin endpoint returns 502.
* **Idempotency.** Re-running a window writes nothing new; revisions are recorded
  as data-quality issues instead of being lost.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.core import time as time_utils
from app.core.logging import get_logger
from app.integrations.elexon.actuals import fetch_wind_actuals
from app.integrations.elexon.client import ElexonClient
from app.integrations.elexon.errors import ElexonError
from app.integrations.elexon.forecasts import fetch_forecast_vintages
from app.repositories.actual_generation_repository import ActualGenerationRepository
from app.repositories.data_quality_repository import DataQualityRepository, QualityIssue
from app.repositories.forecast_vintage_repository import ForecastVintageRepository
from app.repositories.ingestion_run_repository import IngestionRunRepository, RunCounts

logger = get_logger(__name__)

RunType = Literal["backfill", "incremental", "manual"]


@dataclass
class IngestionSummary:
    """The outcome of one ingestion run, safe to serialise to the API."""

    run_id: int
    dataset: str
    status: str
    window_from_utc: datetime
    window_to_utc: datetime
    rows_fetched: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_rejected: int = 0
    http_requests: int = 0
    http_status: int | None = None
    vintages: int = 0
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialise with ISO-8601 UTC timestamps."""
        payload = asdict(self)
        payload["window_from_utc"] = time_utils.format_utc(self.window_from_utc)
        payload["window_to_utc"] = time_utils.format_utc(self.window_to_utc)
        return payload


class IngestionService:
    """Loads FUELHH actuals and WINDFOR vintages into MySQL."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        client: ElexonClient,
        *,
        actual_chunk_days: int = 7,
        forecast_chunk_days: int = 1,
    ) -> None:
        self._session_factory = session_factory
        self._client = client
        self._actual_chunk_days = actual_chunk_days
        self._forecast_chunk_days = forecast_chunk_days
        self._checksums: list[str] = []

    # ── actual generation ────────────────────────────────────────────────
    def ingest_actuals(
        self,
        date_from: date,
        date_to: date,
        *,
        run_type: RunType = "manual",
    ) -> IngestionSummary:
        """Fetch and store WIND outturn for an inclusive settlement-date range."""
        window_from = time_utils.settlement_day_start_utc(date_from)
        window_to = time_utils.settlement_day_end_utc(date_to)
        session = self._session_factory()
        run_id = self._start_run(session, "FUELHH", run_type, window_from, window_to)

        try:
            result = fetch_wind_actuals(
                self._client,
                date_from,
                date_to,
                chunk_days=self._actual_chunk_days,
            )
            counts = RunCounts(
                rows_fetched=len(result.rows) + len(result.rejected),
                rows_rejected=len(result.rejected),
                http_requests=result.requests,
                http_status=result.http_status,
                payload_checksum=self._checksum(),
            )
            repo = ActualGenerationRepository(session)
            upsert = repo.upsert_many(result.rows, run_id)
            counts.rows_inserted = upsert.inserted
            counts.rows_updated = upsert.updated

            issues = [
                QualityIssue(
                    dataset="FUELHH",
                    issue_type=rejected.reason.upper(),
                    severity="warning",
                    detail=rejected.detail,
                )
                for rejected in result.rejected
            ]
            if issues:
                DataQualityRepository(session).add_many(issues, run_id=run_id)

            status = "partial" if result.rejected else "succeeded"
            IngestionRunRepository(session).finish(run_id, status=status, counts=counts)
            IngestionRunRepository(session).set_watermark("FUELHH", run_id, window_to)
            session.commit()

            summary = IngestionSummary(
                run_id=run_id,
                dataset="FUELHH",
                status=status,
                window_from_utc=window_from,
                window_to_utc=window_to,
                rows_fetched=counts.rows_fetched,
                rows_inserted=upsert.inserted,
                rows_updated=upsert.updated,
                rows_rejected=counts.rows_rejected,
                http_requests=counts.http_requests,
                http_status=counts.http_status,
            )
            logger.info("ingestion_actuals_completed", extra=summary.to_dict())
            return summary
        except Exception as exc:
            session.rollback()
            self._mark_failed(run_id, exc)
            raise
        finally:
            session.close()

    # ── forecasts ────────────────────────────────────────────────────────
    def ingest_forecasts(
        self,
        publish_from: datetime,
        publish_to: datetime,
        *,
        run_type: RunType = "manual",
    ) -> IngestionSummary:
        """Fetch and store every WINDFOR vintage published in a window."""
        window_from = time_utils.ensure_utc(publish_from)
        window_to = time_utils.ensure_utc(publish_to)
        session = self._session_factory()
        run_id = self._start_run(session, "WINDFOR", run_type, window_from, window_to)

        try:
            result = fetch_forecast_vintages(
                self._client,
                window_from,
                window_to,
                chunk_days=self._forecast_chunk_days,
            )
            counts = RunCounts(
                rows_fetched=sum(v.source_row_count for v in result.vintages) + len(result.rejected),
                rows_rejected=len(result.rejected),
                http_requests=result.requests,
                http_status=result.http_status,
                payload_checksum=self._checksum(),
            )
            repo = ForecastVintageRepository(session)
            issues: list[QualityIssue] = [
                QualityIssue(
                    dataset="WINDFOR",
                    issue_type=rejected.reason.upper(),
                    severity="warning",
                    detail=rejected.detail,
                )
                for rejected in result.rejected
            ]

            for vintage in result.vintages:
                upsert = repo.upsert_vintage(vintage, run_id)
                counts.rows_inserted += upsert.points_inserted
                counts.rows_updated += upsert.points_updated
                for valid_from, previous, current in upsert.revisions:
                    issues.append(
                        QualityIssue(
                            dataset="WINDFOR",
                            issue_type="REVISED_VALUE",
                            severity="warning",
                            settlement_date=time_utils.period_for_instant(valid_from)[0],
                            settlement_period=time_utils.period_for_instant(valid_from)[1],
                            vintage_publish_time_utc=vintage.publish_time_utc,
                            detail=(
                                f"point {valid_from.isoformat()} changed from {previous} to "
                                f"{current} within vintage {vintage.publish_time_utc.isoformat()}"
                            ),
                        )
                    )

            if issues:
                DataQualityRepository(session).add_many(issues, run_id=run_id)

            status = "partial" if result.rejected else "succeeded"
            IngestionRunRepository(session).finish(run_id, status=status, counts=counts)
            IngestionRunRepository(session).set_watermark("WINDFOR", run_id, window_to)
            session.commit()

            summary = IngestionSummary(
                run_id=run_id,
                dataset="WINDFOR",
                status=status,
                window_from_utc=window_from,
                window_to_utc=window_to,
                rows_fetched=counts.rows_fetched,
                rows_inserted=counts.rows_inserted,
                rows_updated=counts.rows_updated,
                rows_rejected=counts.rows_rejected,
                http_requests=counts.http_requests,
                http_status=counts.http_status,
                vintages=len(result.vintages),
            )
            logger.info("ingestion_forecasts_completed", extra=summary.to_dict())
            return summary
        except Exception as exc:
            session.rollback()
            self._mark_failed(run_id, exc)
            raise
        finally:
            session.close()

    # ── internals ────────────────────────────────────────────────────────
    def _start_run(
        self,
        session: Session,
        dataset: str,
        run_type: str,
        window_from: datetime,
        window_to: datetime,
    ) -> int:
        run = IngestionRunRepository(session).create(
            dataset=dataset,
            run_type=run_type,
            window_from=window_from,
            window_to=window_to,
        )
        session.commit()
        logger.info(
            "ingestion_run_started",
            extra={"run_id": run.id, "dataset": dataset, "run_type": run_type},
        )
        return run.id

    def _mark_failed(self, run_id: int, exc: Exception) -> None:
        """Record the failure in its own transaction so it survives the rollback."""
        code = getattr(exc, "code", type(exc).__name__)
        message = getattr(exc, "message", str(exc))
        http_status = getattr(exc, "http_status", None)
        session = self._session_factory()
        try:
            IngestionRunRepository(session).finish(
                run_id,
                status="failed",
                counts=RunCounts(
                    http_requests=self._client.request_count,
                    http_status=http_status,
                    payload_checksum=self._checksum(),
                ),
                error_code=str(code)[:64],
                error_message=str(message)[:1000],
            )
            session.commit()
        finally:
            session.close()
        logger.error(
            "ingestion_run_failed",
            extra={
                "run_id": run_id,
                "error_code": code,
                "error_message": message,
                "is_upstream": isinstance(exc, ElexonError),
            },
        )

    def _checksum(self) -> str | None:
        """Checksum of the responses this client has served, when available."""
        raw = getattr(self._client, "response_bodies", None)
        if not raw:
            return None
        digest = hashlib.sha256()
        for body in raw:
            digest.update(body.encode("utf-8"))
        return digest.hexdigest()
