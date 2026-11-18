"""Typed read-only definitions for the SQL views created by Alembic.

The views exist so "latest actual revision" and "as-of forecast joined to actual"
have exactly one definition, in SQL, reviewable by a DBA. They are declared here
as core ``Table`` objects rather than ORM mappings because a view has no primary
key of its own.

Declaring them (instead of issuing ``text()`` queries) matters for correctness:
MySQL returns naive datetimes, and ``UTCDateTime`` re-attaches UTC on the way out,
so every timestamp leaving this layer is unambiguous. Read-only: nothing writes
through these tables.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, Integer, MetaData, Numeric, String, Table

from app.models.base import UTCDateTime

view_metadata = MetaData()

actual_generation_latest = Table(
    "v_actual_generation_latest",
    view_metadata,
    Column("id", BigInteger),
    Column("settlement_date", Date),
    Column("settlement_period", Integer),
    Column("fuel_type", String(16)),
    Column("start_time_utc", UTCDateTime()),
    Column("end_time_utc", UTCDateTime()),
    Column("generation_mw", Numeric(10, 2)),
    Column("source_publish_time_utc", UTCDateTime()),
    Column("ingestion_run_id", BigInteger),
    Column("created_at_utc", UTCDateTime()),
    Column("updated_at_utc", UTCDateTime()),
)

analysis_interval = Table(
    "v_analysis_interval",
    view_metadata,
    Column("cutoff_policy_id", Integer),
    Column("settlement_date", Date),
    Column("settlement_period", Integer),
    Column("interval_start_utc", UTCDateTime()),
    Column("cutoff_utc", UTCDateTime()),
    Column("vintage_id", BigInteger),
    Column("vintage_publish_time_utc", UTCDateTime()),
    Column("lead_time_minutes", Integer),
    Column("forecast_mw", Numeric(10, 2)),
    Column("actual_mw", Numeric(10, 2)),
    Column("selection_status", String(24)),
)

forecast_coverage_daily = Table(
    "v_forecast_coverage_daily",
    view_metadata,
    Column("cutoff_policy_id", Integer),
    Column("settlement_date", Date),
    Column("intervals", Integer),
    Column("selected_intervals", Integer),
    Column("missing_intervals", Integer),
    Column("earliest_used_vintage", UTCDateTime()),
    Column("latest_used_vintage", UTCDateTime()),
    Column("min_lead_minutes", Integer),
    Column("max_lead_minutes", Integer),
)
