"""Ingestion bookkeeping: one row per ingestion attempt, plus a per-dataset watermark."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, SMALLINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UTCDateTime

RUN_STATUSES = ("running", "succeeded", "partial", "failed")
RUN_TYPES = ("backfill", "incremental", "manual")
DATASETS = ("FUELHH", "WINDFOR")


class IngestionRun(Base, CreatedAtMixin):
    """A single ingestion attempt over a bounded window.

    ``status`` is the authoritative record of whether data was loaded. Counts are
    exact (computed before the upsert, not inferred from driver row counts).
    """

    __tablename__ = "ingestion_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','succeeded','partial','failed')",
            name="chk_run_status",
        ),
        CheckConstraint("dataset IN ('FUELHH','WINDFOR')", name="chk_run_dataset"),
        CheckConstraint(
            "run_type IN ('backfill','incremental','manual')", name="chk_run_type"
        ),
        Index("ix_run_dataset_started", "dataset", "started_at_utc"),
        Index("ix_run_status", "status", "started_at_utc"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(16), nullable=False)
    run_type: Mapped[str] = mapped_column(String(16), nullable=False)
    window_from_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    window_to_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")

    http_requests: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)
    rows_fetched: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)
    rows_inserted: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)
    rows_updated: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)

    http_status: Mapped[int | None] = mapped_column(SMALLINT(unsigned=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Fixed-length hex digest, matching CHAR(64) in the migration (a varchar
    # would be padded differently and made `alembic check` report drift).
    payload_checksum: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)

    started_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP(6)")
    )
    finished_at_utc: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class IngestionWatermark(Base):
    """Last successfully ingested instant per dataset, for incremental runs."""

    __tablename__ = "ingestion_watermark"
    __table_args__ = (Index("ix_wm_run", "last_run_id"),)

    dataset: Mapped[str] = mapped_column(String(16), primary_key=True)
    last_success_to_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_run_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("ingestion_run.id", ondelete="SET NULL"), nullable=True
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
        onupdate=text("CURRENT_TIMESTAMP(6)"),
    )
