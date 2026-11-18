"""Declarative base and shared column type conventions.

Instants are stored as ``DATETIME(6)`` (not ``TIMESTAMP``) to avoid session-time
conversion and the 2038 limit. Power is stored as ``DECIMAL`` so stored values
never drift.

MySQL's ``DATETIME`` has no timezone, so the driver returns *naive* datetimes.
Treating those as local time would shift data by an hour across a DST boundary,
and passing them to code that requires aware instants raises. ``UTCDateTime``
closes that hole in one place:

* on write, an aware datetime is converted to UTC and stored without tzinfo;
* on read, the value comes back tagged as UTC.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, Numeric, TypeDecorator, func, text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UTCDateTime(TypeDecorator[datetime]):
    """``DATETIME(6)`` that always round-trips as a timezone-aware UTC instant."""

    impl = DATETIME(fsp=6)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        """Store as naive UTC (a naive input is already UTC by convention)."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        """Return every stored instant as an aware UTC datetime."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    """Project declarative base."""

    type_annotation_map = {
        datetime: UTCDateTime(),
        date: Date,
        Decimal: Numeric(12, 4),
    }


class CreatedAtMixin:
    """Adds a UTC creation timestamp with a database-side default."""

    created_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )


class UpdatedAtMixin:
    """Adds a UTC update timestamp maintained by the database and the ORM."""

    updated_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
        onupdate=func.now(),
    )
