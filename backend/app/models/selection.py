"""Materialised as-of forecast selection.

One row per (cutoff policy, settlement date, settlement period). The row records
exactly which vintage was available at the cutoff, its publication time, the
derived lead time and a status describing failure when no eligible vintage
covered the interval. Rows are rebuildable from immutable vintages plus the
policy row.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, SMALLINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UTCDateTime

SELECTION_STATUSES = (
    "selected",
    "no_vintage_before_cutoff",
    "no_point_for_interval",
)


class ForecastSelection(Base):
    """The decision-time forecast for one delivery interval."""

    __tablename__ = "forecast_selection"
    __table_args__ = (
        UniqueConstraint(
            "cutoff_policy_id",
            "settlement_date",
            "settlement_period",
            name="uq_selection",
        ),
        Index("ix_selection_vintage", "vintage_id"),
        Index("ix_selection_date", "settlement_date", "settlement_period"),
        Index("ix_selection_status", "selection_status"),
        CheckConstraint("settlement_period BETWEEN 1 AND 50", name="chk_selection_sp"),
        CheckConstraint(
            "lead_time_minutes IS NULL OR lead_time_minutes >= 0", name="chk_selection_lead"
        ),
        CheckConstraint(
            "selection_status IN ('selected','no_vintage_before_cutoff','no_point_for_interval')",
            name="chk_selection_status",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    cutoff_policy_id: Mapped[int] = mapped_column(
        SMALLINT(unsigned=True),
        ForeignKey("cutoff_policy.id", ondelete="RESTRICT"),
        nullable=False,
    )
    settlement_date: Mapped[date] = mapped_column(nullable=False)
    settlement_period: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    interval_start_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    cutoff_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    vintage_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("forecast_vintage.id", ondelete="RESTRICT"),
        nullable=True,
    )
    vintage_publish_time_utc: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    lead_time_minutes: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    forecast_mw: Mapped[Decimal | None] = mapped_column(nullable=True)
    fallback_depth: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=0)
    selection_status: Mapped[str] = mapped_column(String(24), nullable=False)
    selected_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP(6)")
    )
