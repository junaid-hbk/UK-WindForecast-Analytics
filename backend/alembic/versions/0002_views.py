"""Analysis views: latest actual revision, analysis join, daily coverage.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

VIEW_LATEST_ACTUAL = """
CREATE VIEW v_actual_generation_latest AS
SELECT a.id,
       a.settlement_date,
       a.settlement_period,
       a.fuel_type,
       a.start_time_utc,
       a.end_time_utc,
       a.generation_mw,
       a.source_publish_time_utc,
       a.ingestion_run_id,
       a.created_at_utc,
       a.updated_at_utc
FROM actual_generation a
JOIN (
  SELECT settlement_date, settlement_period, fuel_type,
         MAX(source_publish_time_utc) AS max_publish
  FROM actual_generation
  GROUP BY settlement_date, settlement_period, fuel_type
) m
  ON  m.settlement_date   = a.settlement_date
  AND m.settlement_period = a.settlement_period
  AND m.fuel_type         = a.fuel_type
  AND m.max_publish       = a.source_publish_time_utc
"""

VIEW_ANALYSIS = """
CREATE VIEW v_analysis_interval AS
SELECT s.cutoff_policy_id,
       s.settlement_date,
       s.settlement_period,
       s.interval_start_utc,
       s.cutoff_utc,
       s.vintage_id,
       s.vintage_publish_time_utc,
       s.lead_time_minutes,
       s.forecast_mw,
       a.generation_mw AS actual_mw,
       s.selection_status
FROM forecast_selection s
LEFT JOIN v_actual_generation_latest a
  ON  a.settlement_date   = s.settlement_date
  AND a.settlement_period = s.settlement_period
  AND a.fuel_type         = 'WIND'
"""

VIEW_COVERAGE = """
CREATE VIEW v_forecast_coverage_daily AS
SELECT s.cutoff_policy_id,
       s.settlement_date,
       COUNT(*)                                        AS intervals,
       SUM(s.selection_status = 'selected')            AS selected_intervals,
       SUM(s.vintage_id IS NULL)                       AS missing_intervals,
       MIN(s.vintage_publish_time_utc)                 AS earliest_used_vintage,
       MAX(s.vintage_publish_time_utc)                 AS latest_used_vintage,
       MIN(s.lead_time_minutes)                        AS min_lead_minutes,
       MAX(s.lead_time_minutes)                        AS max_lead_minutes
FROM forecast_selection s
GROUP BY s.cutoff_policy_id, s.settlement_date
"""


def upgrade() -> None:
    op.execute(VIEW_LATEST_ACTUAL)
    op.execute(VIEW_ANALYSIS)
    op.execute(VIEW_COVERAGE)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_forecast_coverage_daily")
    op.execute("DROP VIEW IF EXISTS v_analysis_interval")
    op.execute("DROP VIEW IF EXISTS v_actual_generation_latest")
