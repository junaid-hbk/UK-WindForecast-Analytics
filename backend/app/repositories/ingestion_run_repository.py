"""Ingestion run bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.core import time as time_utils
from app.models.ingestion import IngestionRun, IngestionWatermark
from app.repositories.base import BaseRepository


@dataclass
class RunCounts:
    """Counts recorded against an ingestion run."""

    rows_fetched: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_rejected: int = 0
    http_requests: int = 0
    http_status: int | None = None
    payload_checksum: str | None = None


class IngestionRunRepository(BaseRepository):
    """Create and close ingestion runs; manage the incremental watermark."""

    def create(
        self, *, dataset: str, run_type: str, window_from: datetime, window_to: datetime
    ) -> IngestionRun:
        """Insert a ``running`` row and flush so its id is available."""
        run = IngestionRun(
            dataset=dataset,
            run_type=run_type,
            window_from_utc=window_from,
            window_to_utc=window_to,
            status="running",
        )
        self.session.add(run)
        self.session.flush()
        return run

    def get(self, run_id: int) -> IngestionRun | None:
        """Return a run by id."""
        return self.session.get(IngestionRun, run_id)

    def finish(
        self,
        run_id: int,
        *,
        status: str,
        counts: RunCounts,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Close a run with its final status and counts."""
        run = self.session.get(IngestionRun, run_id)
        if run is None:
            return
        run.status = status
        run.rows_fetched = counts.rows_fetched
        run.rows_inserted = counts.rows_inserted
        run.rows_updated = counts.rows_updated
        run.rows_rejected = counts.rows_rejected
        run.http_requests = counts.http_requests
        run.http_status = counts.http_status
        run.payload_checksum = counts.payload_checksum
        run.error_code = error_code
        run.error_message = error_message
        run.finished_at_utc = time_utils.utc_now()

    def recent(self, *, limit: int = 50, dataset: str | None = None) -> list[IngestionRun]:
        """Most recent runs, newest first."""
        stmt = select(IngestionRun).order_by(IngestionRun.started_at_utc.desc(), IngestionRun.id.desc())
        if dataset is not None:
            stmt = stmt.where(IngestionRun.dataset == dataset)
        return list(self.session.scalars(stmt.limit(limit)))

    def latest_success(self, dataset: str) -> IngestionRun | None:
        """Most recent successful run for a dataset."""
        stmt = (
            select(IngestionRun)
            .where(IngestionRun.dataset == dataset, IngestionRun.status.in_(("succeeded", "partial")))
            .order_by(IngestionRun.finished_at_utc.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def set_watermark(self, dataset: str, run_id: int, watermark_utc: datetime) -> None:
        """Advance the dataset watermark (never backwards)."""
        record = self.session.get(IngestionWatermark, dataset)
        if record is None:
            record = IngestionWatermark(
                dataset=dataset, last_success_to_utc=watermark_utc, last_run_id=run_id
            )
            self.session.add(record)
            return
        if watermark_utc > record.last_success_to_utc:
            record.last_success_to_utc = watermark_utc
        record.last_run_id = run_id

    def get_watermark(self, dataset: str) -> IngestionWatermark | None:
        """Return the stored watermark for a dataset."""
        return self.session.get(IngestionWatermark, dataset)
