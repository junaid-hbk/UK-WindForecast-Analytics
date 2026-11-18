"""Initial schema: actuals, forecast vintages, selections, runs, policies.

Written as explicit DDL so the migration is the reviewable source of truth for
types, constraints and indexes (rather than a snapshot of ORM metadata).

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = (
    """
    CREATE TABLE ingestion_run (
      id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      dataset             VARCHAR(16)  NOT NULL,
      run_type            VARCHAR(16)  NOT NULL,
      window_from_utc     DATETIME(6)  NOT NULL,
      window_to_utc       DATETIME(6)  NOT NULL,
      status              VARCHAR(16)  NOT NULL,
      http_requests       INT UNSIGNED NOT NULL DEFAULT 0,
      rows_fetched        INT UNSIGNED NOT NULL DEFAULT 0,
      rows_inserted       INT UNSIGNED NOT NULL DEFAULT 0,
      rows_updated        INT UNSIGNED NOT NULL DEFAULT 0,
      rows_rejected       INT UNSIGNED NOT NULL DEFAULT 0,
      http_status         SMALLINT UNSIGNED NULL,
      error_code          VARCHAR(64)  NULL,
      error_message       VARCHAR(1000) NULL,
      payload_checksum    CHAR(64)     NULL,
      started_at_utc      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      finished_at_utc     DATETIME(6)  NULL,
      created_at_utc      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      PRIMARY KEY (id),
      KEY ix_run_dataset_started (dataset, started_at_utc),
      KEY ix_run_status (status, started_at_utc),
      CONSTRAINT chk_run_status
        CHECK (status IN ('running','succeeded','partial','failed')),
      CONSTRAINT chk_run_dataset CHECK (dataset IN ('FUELHH','WINDFOR')),
      CONSTRAINT chk_run_type CHECK (run_type IN ('backfill','incremental','manual'))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE ingestion_watermark (
      dataset              VARCHAR(16) NOT NULL,
      last_success_to_utc  DATETIME(6) NOT NULL,
      last_run_id          BIGINT UNSIGNED NULL,
      updated_at_utc       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                       ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (dataset),
      KEY ix_wm_run (last_run_id),
      CONSTRAINT fk_wm_run FOREIGN KEY (last_run_id)
        REFERENCES ingestion_run (id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE cutoff_policy (
      id                SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
      code              VARCHAR(32)  NOT NULL,
      name              VARCHAR(120) NOT NULL,
      local_time        TIME         NOT NULL,
      timezone_id       VARCHAR(64)  NOT NULL DEFAULT 'Europe/London',
      offset_days       SMALLINT     NOT NULL DEFAULT -1,
      is_default        TINYINT(1)   NOT NULL DEFAULT 0,
      source_reference  VARCHAR(255) NULL,
      notes             VARCHAR(500) NULL,
      created_at_utc    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      updated_at_utc    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                     ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (id),
      UNIQUE KEY uq_policy_code (code),
      KEY ix_policy_default (is_default),
      CONSTRAINT chk_policy_offset CHECK (offset_days BETWEEN -7 AND 0)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE forecast_vintage (
      id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      dataset              VARCHAR(16) NOT NULL DEFAULT 'WINDFOR',
      publish_time_utc     DATETIME(6) NOT NULL,
      horizon_start_utc    DATETIME(6) NOT NULL,
      horizon_end_utc      DATETIME(6) NOT NULL,
      resolution_minutes   SMALLINT UNSIGNED NOT NULL DEFAULT 60,
      point_count          SMALLINT UNSIGNED NOT NULL DEFAULT 0,
      source_row_count     INT UNSIGNED NOT NULL DEFAULT 0,
      first_run_id         BIGINT UNSIGNED NULL,
      last_seen_run_id     BIGINT UNSIGNED NULL,
      created_at_utc       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      updated_at_utc       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                      ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (id),
      UNIQUE KEY uq_vintage_dataset_publish (dataset, publish_time_utc),
      KEY ix_vintage_publish (publish_time_utc),
      KEY ix_vintage_horizon (horizon_start_utc, horizon_end_utc),
      CONSTRAINT chk_vintage_resolution CHECK (resolution_minutes > 0),
      CONSTRAINT fk_vintage_first_run FOREIGN KEY (first_run_id)
        REFERENCES ingestion_run (id) ON DELETE SET NULL,
      CONSTRAINT fk_vintage_last_run FOREIGN KEY (last_seen_run_id)
        REFERENCES ingestion_run (id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE forecast_point (
      vintage_id      BIGINT UNSIGNED NOT NULL,
      valid_from_utc  DATETIME(6) NOT NULL,
      valid_to_utc    DATETIME(6) NOT NULL,
      generation_mw   DECIMAL(12,4) NULL,
      created_at_utc  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      PRIMARY KEY (vintage_id, valid_from_utc),
      KEY ix_point_valid_from (valid_from_utc),
      CONSTRAINT chk_point_window CHECK (valid_to_utc > valid_from_utc),
      CONSTRAINT fk_point_vintage FOREIGN KEY (vintage_id)
        REFERENCES forecast_vintage (id) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE actual_generation (
      id                       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      settlement_date          DATE NOT NULL,
      settlement_period        TINYINT UNSIGNED NOT NULL,
      fuel_type                VARCHAR(16) NOT NULL DEFAULT 'WIND',
      start_time_utc           DATETIME(6) NOT NULL,
      end_time_utc             DATETIME(6) NOT NULL,
      generation_mw            DECIMAL(12,4) NULL,
      source_publish_time_utc  DATETIME(6) NOT NULL,
      ingestion_run_id         BIGINT UNSIGNED NULL,
      created_at_utc           DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      updated_at_utc           DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                            ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (id),
      UNIQUE KEY uq_actual_revision
        (settlement_date, settlement_period, fuel_type, source_publish_time_utc),
      KEY ix_actual_lookup (fuel_type, settlement_date, settlement_period),
      KEY ix_actual_start (start_time_utc),
      CONSTRAINT chk_actual_sp CHECK (settlement_period BETWEEN 1 AND 50),
      CONSTRAINT chk_actual_window CHECK (end_time_utc > start_time_utc),
      CONSTRAINT fk_actual_run FOREIGN KEY (ingestion_run_id)
        REFERENCES ingestion_run (id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE forecast_selection (
      id                       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      cutoff_policy_id         SMALLINT UNSIGNED NOT NULL,
      settlement_date          DATE NOT NULL,
      settlement_period        TINYINT UNSIGNED NOT NULL,
      interval_start_utc       DATETIME(6) NOT NULL,
      cutoff_utc               DATETIME(6) NOT NULL,
      vintage_id               BIGINT UNSIGNED NULL,
      vintage_publish_time_utc DATETIME(6) NULL,
      lead_time_minutes        INT NULL,
      forecast_mw              DECIMAL(12,4) NULL,
      fallback_depth           TINYINT UNSIGNED NOT NULL DEFAULT 0,
      selection_status         VARCHAR(24) NOT NULL,
      selected_at_utc          DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      PRIMARY KEY (id),
      UNIQUE KEY uq_selection (cutoff_policy_id, settlement_date, settlement_period),
      KEY ix_selection_vintage (vintage_id),
      KEY ix_selection_date (settlement_date, settlement_period),
      KEY ix_selection_status (selection_status),
      CONSTRAINT chk_selection_sp CHECK (settlement_period BETWEEN 1 AND 50),
      CONSTRAINT chk_selection_lead
        CHECK (lead_time_minutes IS NULL OR lead_time_minutes >= 0),
      CONSTRAINT chk_selection_status
        CHECK (selection_status IN ('selected','no_vintage_before_cutoff','no_point_for_interval')),
      CONSTRAINT fk_selection_policy FOREIGN KEY (cutoff_policy_id)
        REFERENCES cutoff_policy (id) ON DELETE RESTRICT,
      CONSTRAINT fk_selection_vintage FOREIGN KEY (vintage_id)
        REFERENCES forecast_vintage (id) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE data_quality_issue (
      id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      ingestion_run_id BIGINT UNSIGNED NULL,
      dataset          VARCHAR(16) NOT NULL,
      issue_type       VARCHAR(48) NOT NULL,
      severity         VARCHAR(8)  NOT NULL,
      settlement_date  DATE NULL,
      settlement_period TINYINT UNSIGNED NULL,
      vintage_publish_time_utc DATETIME(6) NULL,
      detail           VARCHAR(1000) NULL,
      created_at_utc   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      PRIMARY KEY (id),
      KEY ix_dqi_type_created (issue_type, created_at_utc),
      KEY ix_dqi_date (settlement_date, settlement_period),
      CONSTRAINT chk_dqi_severity CHECK (severity IN ('info','warning','error')),
      CONSTRAINT fk_dqi_run FOREIGN KEY (ingestion_run_id)
        REFERENCES ingestion_run (id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
)


def upgrade() -> None:
    for statement in TABLES:
        op.execute(statement)


def downgrade() -> None:
    for table in (
        "data_quality_issue",
        "forecast_selection",
        "actual_generation",
        "forecast_point",
        "forecast_vintage",
        "cutoff_policy",
        "ingestion_watermark",
        "ingestion_run",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
