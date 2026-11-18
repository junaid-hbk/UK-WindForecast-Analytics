"""Forecast vintages and their hourly points.

A *vintage* is one published WINDFOR file, identified by ``publish_time_utc``.
Vintages are append-only: nothing in the application updates or deletes a
vintage row, and its points keep WINDFOR's native hourly resolution. Mapping to
half-hourly settlement periods happens at analysis time so no invented values are
persisted.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, SMALLINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UTCDateTime, UpdatedAtMixin


class ForecastVintage(Base, CreatedAtMixin, UpdatedAtMixin):
    """One published WINDFOR forecast file."""

    __tablename__ = "forecast_vintage"
    __table_args__ = (
        UniqueConstraint(
            "dataset", "publish_time_utc", name="uq_vintage_dataset_publish"
        ),
        Index("ix_vintage_publish", "publish_time_utc"),
        Index("ix_vintage_horizon", "horizon_start_utc", "horizon_end_utc"),
        CheckConstraint("resolution_minutes > 0", name="chk_vintage_resolution"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(16), nullable=False, default="WINDFOR")
    publish_time_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    horizon_start_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    horizon_end_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(
        SMALLINT(unsigned=True), nullable=False, default=60
    )
    point_count: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False, default=0)
    source_row_count: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), nullable=False, default=0
    )
    first_run_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("ingestion_run.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_seen_run_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("ingestion_run.id", ondelete="SET NULL"),
        nullable=True,
    )

    points: Mapped[list["ForecastPoint"]] = relationship(
        back_populates="vintage", cascade="all, delete-orphan", order_by="ForecastPoint.valid_from_utc"
    )


class ForecastPoint(Base):
    """One hourly value inside a vintage, valid for ``[valid_from, valid_to)``."""

    __tablename__ = "forecast_point"
    __table_args__ = (
        Index("ix_point_valid_from", "valid_from_utc"),
        CheckConstraint("valid_to_utc > valid_from_utc", name="chk_point_window"),
    )

    vintage_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("forecast_vintage.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    valid_from_utc: Mapped[datetime] = mapped_column(UTCDateTime(), primary_key=True)
    valid_to_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    generation_mw: Mapped[Decimal | None] = mapped_column(nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=text("CURRENT_TIMESTAMP(6)")
    )

    vintage: Mapped[ForecastVintage] = relationship(back_populates="points")
