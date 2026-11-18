"""Data-quality issues raised during ingestion or selection.

Issues are how missing/odd data becomes visible instead of being silently
coerced (for example a forecast published only after the cutoff, or a rejected
row).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UTCDateTime

SEVERITIES = ("info", "warning", "error")


class DataQualityIssue(Base, CreatedAtMixin):
    """A single recorded data problem."""

    __tablename__ = "data_quality_issue"
    __table_args__ = (
        Index("ix_dqi_type_created", "issue_type", "created_at_utc"),
        Index("ix_dqi_date", "settlement_date", "settlement_period"),
        CheckConstraint(
            "severity IN ('info','warning','error')", name="chk_dqi_severity"
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("ingestion_run.id", ondelete="SET NULL"),
        nullable=True,
    )
    dataset: Mapped[str] = mapped_column(String(16), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False, default="warning")
    settlement_date: Mapped[date | None] = mapped_column(nullable=True)
    settlement_period: Mapped[int | None] = mapped_column(TINYINT(unsigned=True), nullable=True)
    vintage_publish_time_utc: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(1000), nullable=True)
