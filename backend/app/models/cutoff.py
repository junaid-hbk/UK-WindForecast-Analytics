"""Configurable day-ahead decision cutoffs.

The cutoff is data, not a constant: it is seeded by an Alembic migration with a
documented source, and may be changed without touching code. Every selection row
records the policy that produced it.
"""

from __future__ import annotations

from datetime import time

from sqlalchemy import CheckConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import SMALLINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UpdatedAtMixin


class CutoffPolicy(Base, CreatedAtMixin, UpdatedAtMixin):
    """A named day-ahead gate-closure rule."""

    __tablename__ = "cutoff_policy"
    __table_args__ = (
        UniqueConstraint("code", name="uq_policy_code"),
        Index("ix_policy_default", "is_default"),
        CheckConstraint("offset_days BETWEEN -7 AND 0", name="chk_policy_offset"),
    )

    id: Mapped[int] = mapped_column(SMALLINT(unsigned=True), primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    local_time: Mapped[time] = mapped_column(nullable=False)
    timezone_id: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    offset_days: Mapped[int] = mapped_column(SMALLINT, nullable=False, default=-1)
    is_default: Mapped[bool] = mapped_column(TINYINT(1), nullable=False, default=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
