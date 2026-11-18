"""Command-line entry point for ingestion and maintenance.

Examples::

    python -m app.cli backfill --from 2026-01-01 --to 2026-02-28
    python -m app.cli actuals --from 2026-01-01 --to 2026-01-07
    python -m app.cli forecasts --from 2026-01-01T00:00:00Z --to 2026-01-02T00:00:00Z
    python -m app.cli selections --from 2026-01-01 --to 2026-02-28
    python -m app.cli verify --from 2026-01-01 --to 2026-02-28

Exit status is non-zero when an ingestion run fails, so CI/cron can detect it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from typing import Any

from app.core import time as time_utils
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import get_session_factory, session_scope
from app.integrations.elexon.client import ElexonClient
from app.repositories.data_status_repository import DataStatusRepository
from app.repositories.forecast_selection_repository import ForecastSelectionRepository
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.services.forecast_selection_service import ForecastSelectionService
from app.services.ingestion_service import IngestionService

logger = get_logger(__name__)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return time_utils.ensure_utc(parsed)


def _client() -> ElexonClient:
    settings = get_settings()
    return ElexonClient(
        base_url=settings.elexon_base_url,
        connect_timeout_seconds=settings.elexon_connect_timeout_seconds,
        read_timeout_seconds=settings.elexon_read_timeout_seconds,
        max_attempts=settings.elexon_max_attempts,
        backoff_base_seconds=settings.elexon_backoff_base_seconds,
        backoff_max_seconds=settings.elexon_backoff_max_seconds,
        user_agent=settings.elexon_user_agent,
    )


def _ingestion() -> IngestionService:
    settings = get_settings()
    return IngestionService(
        get_session_factory(),
        _client(),
        actual_chunk_days=settings.elexon_actual_chunk_days,
        forecast_chunk_days=settings.elexon_forecast_chunk_days,
    )


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, default=str))


def cmd_actuals(args: argparse.Namespace) -> int:
    summary = _ingestion().ingest_actuals(
        args.date_from, args.date_to, run_type=args.run_type
    )
    _print(summary.to_dict())
    return 0 if summary.status in ("succeeded", "partial") else 1


def cmd_forecasts(args: argparse.Namespace) -> int:
    summary = _ingestion().ingest_forecasts(
        args.instant_from, args.instant_to, run_type=args.run_type
    )
    _print(summary.to_dict())
    return 0 if summary.status in ("succeeded", "partial") else 1


def cmd_selections(args: argparse.Namespace) -> int:
    settings = get_settings()
    with session_scope() as session:
        summary = ForecastSelectionService(
            session, mapping=settings.windfor_sp_mapping
        ).rebuild(args.date_from, args.date_to, policy_code=args.policy)
    _print(
        {
            "policy_code": summary.policy_code,
            "cutoff_definition": summary.cutoff_definition,
            "date_from": summary.date_from.isoformat(),
            "date_to": summary.date_to.isoformat(),
            "mapping": summary.mapping,
            "intervals": summary.intervals,
            "selected": summary.selected,
            "no_vintage_before_cutoff": summary.no_vintage_before_cutoff,
            "no_point_for_interval": summary.no_point_for_interval,
            "fallback_intervals": summary.fallback_intervals,
            "max_fallback_depth": summary.max_fallback_depth,
            "min_lead_minutes": summary.min_lead_minutes,
            "max_lead_minutes": summary.max_lead_minutes,
            "vintages_considered": summary.vintages_considered,
            "days_with_missing_intervals": summary.missing_days,
        }
    )
    return 0


def cmd_backfill(args: argparse.Namespace) -> int:
    """Actuals + every needed vintage + selections, in dependency order."""
    date_from: date = args.date_from
    date_to: date = args.date_to
    # A delivery day needs vintages published from three days before it, and the
    # last delivery day needs vintages published up to a day after it.
    publish_from = time_utils.settlement_day_start_utc(date_from - timedelta(days=3))
    publish_to = time_utils.settlement_day_end_utc(date_to + timedelta(days=1))

    service = _ingestion()
    actuals = service.ingest_actuals(date_from, date_to, run_type="backfill")
    _print(actuals.to_dict())
    if actuals.status == "failed":
        return 1

    forecasts = service.ingest_forecasts(publish_from, publish_to, run_type="backfill")
    _print(forecasts.to_dict())
    if forecasts.status == "failed":
        return 1

    return cmd_selections(args)


def cmd_verify(args: argparse.Namespace) -> int:
    settings = get_settings()
    with session_scope() as session:
        policy = CutoffPolicyRepository(session).resolve(args.policy)
        status_repo = DataStatusRepository(session)
        coverage = status_repo.coverage(policy.id, args.date_from, args.date_to)
        _print(
            {
                "policy": policy.code,
                "mapping": settings.windfor_sp_mapping,
                "forecast": status_repo.forecast_counts(),
                "actual": status_repo.actual_counts(),
                "latest_vintage_publish_time_utc": (
                    time_utils.format_utc(status_repo.latest_vintage().publish_time_utc)
                    if status_repo.latest_vintage()
                    else None
                ),
                "latest_actual_settlement_date": status_repo.latest_actual_date(),
                "selection_rows": ForecastSelectionRepository(session).count_range(
                    policy.id, args.date_from, args.date_to
                ),
                "coverage_days": len(coverage),
                "days_with_gaps": sum(1 for day in coverage if day.missing_intervals > 0),
            }
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI parser."""
    parser = argparse.ArgumentParser(prog="windpulse", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    actuals = sub.add_parser("actuals", help="Ingest FUELHH WIND outturn")
    actuals.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    actuals.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    actuals.add_argument(
        "--run-type", dest="run_type", default="manual", choices=["manual", "incremental", "backfill"]
    )
    actuals.set_defaults(func=cmd_actuals)

    forecasts = sub.add_parser("forecasts", help="Ingest WINDFOR vintages")
    forecasts.add_argument("--from", dest="instant_from", type=_parse_instant, required=True)
    forecasts.add_argument("--to", dest="instant_to", type=_parse_instant, required=True)
    forecasts.add_argument(
        "--run-type", dest="run_type", default="manual", choices=["manual", "incremental", "backfill"]
    )
    forecasts.set_defaults(func=cmd_forecasts)

    selections = sub.add_parser("selections", help="Rebuild as-of selections")
    selections.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    selections.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    selections.add_argument("--policy", dest="policy", default=None)
    selections.set_defaults(func=cmd_selections)

    backfill = sub.add_parser("backfill", help="Actuals + forecasts + selections")
    backfill.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    backfill.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    backfill.add_argument("--policy", dest="policy", default=None)
    backfill.set_defaults(func=cmd_backfill)

    verify = sub.add_parser("verify", help="Report stored data counts and coverage")
    verify.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    verify.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    verify.add_argument("--policy", dest="policy", default=None)
    verify.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    settings = get_settings()
    configure_logging(settings.log_level)
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # surface the real error, then fail loudly
        logger.error(
            "cli_command_failed",
            extra={"command": args.command, "error": repr(exc)},
        )
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
