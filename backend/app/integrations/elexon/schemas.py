"""Pydantic models for Elexon stream payloads.

Shapes verified against live responses on 2026-11-16:

* ``/datasets/FUELHH/stream`` returns a **bare JSON array** of rows with
  ``dataset, publishTime, startTime, settlementDate, settlementPeriod,
  fuelType, generation``;
* ``/datasets/WINDFOR/stream`` returns a bare array of rows with
  ``dataset, publishTime, startTime, generation`` and *no* settlement fields.

The documented FUELHH example shows ``"dataset": "FUELINST"`` (a documentation
copy error) and the live payload returns ``FUELHH``; the ``dataset`` value is
therefore recorded but never trusted for routing.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class _ElexonRow(BaseModel):
    """Common behaviour: ignore unknown fields, coerce naive timestamps to UTC."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    @field_validator("publishTime", "startTime", check_fields=False)
    @classmethod
    def _as_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class FuelHhRow(_ElexonRow):
    """One FUELHH generation-outturn row."""

    dataset: str | None = None
    publishTime: datetime
    startTime: datetime
    settlementDate: date | None = None
    settlementPeriod: int | None = None
    fuelType: str
    generation: Decimal | None = None


class WindForRow(_ElexonRow):
    """One WINDFOR forecast row (hourly resolution, nationality-wide)."""

    dataset: str | None = None
    publishTime: datetime
    startTime: datetime
    generation: Decimal | None = None
