"""Seed day-ahead cutoff policies with their sources.

The default is the earliest GB hourly day-ahead gate closure (EPEX SPOT GB
Day-Ahead 60-minute auction, 09:20 Europe/London on D-1), which is the
conservative choice: it cannot admit information published after any of the
hourly day-ahead auctions closes.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import bindparam, text

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

POLICIES = (
    (
        "EPEX_GB_DA_1H_0920",
        "EPEX SPOT GB Day-Ahead 60-minute auction gate closure (D-1 09:20 London)",
        "09:20:00",
        -1,
        1,
        "EPEX SPOT Operational Rules: 'EPEX SPOT Day-Ahead GB 60min Auction "
        "(09:20 GMT/BST, D-1)'; DESNZ consultation response references the GB hourly "
        "day-ahead auctions at 09:20 and 09:50.",
        "Default policy. Conservative: earliest of the GB hourly day-ahead gate closures.",
    ),
    (
        "N2EX_GB_DA_1H_0950",
        "Nord Pool N2EX GB day-ahead auction gate closure (D-1 09:50 London)",
        "09:50:00",
        -1,
        0,
        "Nord Pool N2EX support article: gate closure 09:50 GMT, results published by "
        "10:00 GMT.",
        "Alternative commercial assumption; 30 minutes later than the EPEX closure.",
    ),
    (
        "EPEX_GB_DA_30M_1530",
        "EPEX SPOT GB Day-Ahead 30-minute auction gate closure (D-1 15:30 London)",
        "15:30:00",
        -1,
        0,
        "EPEX SPOT Operational Rules: 'EPEX SPOT Day-Ahead GB 30min Auction "
        "(15.30 GMT/BST, D-1)'.",
        "Later cutoff: shows how much fresher information a later auction buys.",
    ),
)


INSERT_POLICY = text(
    """
    INSERT INTO cutoff_policy
      (code, name, local_time, timezone_id, offset_days, is_default,
       source_reference, notes)
    VALUES
      (:code, :name, :local_time, 'Europe/London', :offset_days,
       :is_default, :source_reference, :notes)
    ON DUPLICATE KEY UPDATE
      name = VALUES(name),
      local_time = VALUES(local_time),
      offset_days = VALUES(offset_days),
      is_default = VALUES(is_default),
      source_reference = VALUES(source_reference),
      notes = VALUES(notes)
    """
)

DELETE_POLICIES = text(
    "DELETE FROM cutoff_policy WHERE code IN :codes"
).bindparams(bindparam("codes", expanding=True))


def upgrade() -> None:
    """Seed the three documented GB day-ahead gate-closure policies.

    Values are bound as parameters rather than interpolated, because the source
    citations contain single quotes (for example ``'EPEX SPOT Day-Ahead GB 60min
    Auction (09:20 GMT/BST, D-1)'``) which would break string-built SQL.
    """
    connection = op.get_bind()
    for code, name, local_time, offset_days, is_default, source, notes in POLICIES:
        connection.execute(
            INSERT_POLICY,
            {
                "code": code,
                "name": name,
                "local_time": local_time,
                "offset_days": offset_days,
                "is_default": is_default,
                "source_reference": source,
                "notes": notes,
            },
        )


def downgrade() -> None:
    op.get_bind().execute(DELETE_POLICIES, {"codes": [code for code, *_ in POLICIES]})
