"""Actual half-hourly wind generation from FUELHH.

Revisions are preserved. FUELHH publishes each settlement period with its own
``publishTime``; if a period is republished, a new row is written and the
``v_actual_generation_latest`` view exposes only the newest revision. Nothing is
overwritten, so an outturn revision remains auditable.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UTCDateTime, UpdatedAtMixin


class ActualGeneration(Base, CreatedAtMixin, UpdatedAtMixin):
    """One published value of national wind outturn for a settlement period."""

    __tablename__ = "actual_generation"
    __table_args__ = (
        UniqueConstraint(
            "settlement_date",
            "settlement_period",
            "fuel_type",
            "source_publish_time_utc",
            name="uq_actual_revision",
        ),
        Index("ix_actual_lookup", "fuel_type", "settlement_date", "settlement_period"),
        Index("ix_actual_start", "start_time_utc"),
        CheckConstraint(
            "settlement_period BETWEEN 1 AND 50", name="chk_actual_sp"
        ),
        CheckConstraint("end_time_utc > start_time_utc", name="chk_actual_window"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    settlement_date: Mapped[date] = mapped_column(nullable=False)
    settlement_period: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(16), nullable=False, default="WIND")
    start_time_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    end_time_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    generation_mw: Mapped[Decimal | None] = mapped_column(nullable=True)
    source_publish_time_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("ingestion_run.id", ondelete="SET NULL"),
        nullable=True,
    )
