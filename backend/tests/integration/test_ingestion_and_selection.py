"""Ingestion and as-of selection end to end against MySQL (mocked HTTP)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import time as time_utils
from app.integrations.elexon.errors import ElexonParameterError
from app.models.forecast import ForecastVintage
from app.models.ingestion import IngestionRun
from app.models.quality import DataQualityIssue
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.data_status_repository import DataStatusRepository
from app.repositories.forecast_selection_repository import ForecastSelectionRepository
from app.services.forecast_selection_service import ForecastSelectionService
from app.services.ingestion_service import IngestionService
from tests.fixtures.builders import add_actual, add_vintage, fuelhh_row, hourly_points
from tests.fixtures.builders import windfor_row

DAY = date(2026, 1, 15)
CUTOFF = datetime(2026, 1, 14, 9, 20, tzinfo=timezone.utc)


class FakeClient:
    """Deterministic Elexon stand-in; records calls, can be told to fail."""

    def __init__(self, rows=None, *, error: Exception | None = None) -> None:
        self.rows = rows or []
        self.error = error
        self.last_status = 200
        self.request_count = 0
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_rows(self, path: str, params: dict[str, object]) -> list[dict[str, object]]:
        self.calls.append((path, params))
        self.request_count += 1
        if self.error is not None:
            raise self.error
        return self.rows

    def close(self) -> None:
        return None


class TestActualIngestion:
    def test_ingest_then_reingest_is_idempotent(self, session_factory) -> None:
        rows = [fuelhh_row(settlement_date=DAY, settlement_period=p, generation=10_000 + p) for p in range(1, 49)]
        service = IngestionService(session_factory, FakeClient(rows))

        first = service.ingest_actuals(DAY, DAY, run_type="manual")
        assert first.status == "succeeded"
        assert first.rows_inserted == 48

        second = service.ingest_actuals(DAY, DAY, run_type="manual")
        assert second.status == "succeeded"
        assert second.rows_inserted == 0

        with session_factory() as db:
            assert len(ActualRows(db)) == 48
            runs = db.scalars(select(IngestionRun)).all()
            assert len(runs) == 2
            assert all(run.status == "succeeded" for run in runs)
            assert runs[0].http_requests == 1

    def test_upstream_failure_preserves_existing_data_and_records_the_run(
        self, session_factory
    ) -> None:
        rows = [fuelhh_row(settlement_date=DAY, settlement_period=p, generation=10_000) for p in range(1, 49)]
        IngestionService(session_factory, FakeClient(rows)).ingest_actuals(DAY, DAY)

        failing = FakeClient(error=ElexonParameterError("bad window", http_status=400))
        service = IngestionService(session_factory, failing)
        with pytest.raises(ElexonParameterError):
            service.ingest_actuals(DAY, DAY)

        with session_factory() as db:
            assert len(ActualRows(db)) == 48
            runs = db.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
            assert runs[-1].status == "failed"
            assert runs[-1].error_code == "ELEXON_PARAMETER_ERROR"
            assert runs[-1].http_status == 400


class TestForecastIngestion:
    def test_vintages_are_stored_separately(self, session_factory) -> None:
        baseline = datetime(2026, 1, 14, 6, tzinfo=timezone.utc)
        rows = []
        for publish, value in (
            (baseline, 1000),
            (baseline + timedelta(hours=2), 1200),
        ):
            for offset in range(4):
                rows.append(
                    windfor_row(
                        publish_time=publish,
                        start_time=datetime(2026, 1, 14, 21, tzinfo=timezone.utc)
                        + timedelta(hours=offset),
                        generation=value + offset,
                    )
                )
        service = IngestionService(session_factory, FakeClient(rows))
        summary = service.ingest_forecasts(baseline, baseline + timedelta(hours=6))

        assert summary.status == "succeeded"
        assert summary.vintages == 2
        assert summary.rows_inserted == 8

        with session_factory() as db:
            vintages = db.scalars(
                select(ForecastVintage).order_by(ForecastVintage.publish_time_utc)
            ).all()
            assert len(vintages) == 2
            assert vintages[0].point_count == 4
            assert vintages[0].horizon_start_utc == datetime(2026, 1, 14, 21, tzinfo=timezone.utc)

    def test_reingest_does_not_create_duplicate_vintages(self, session_factory) -> None:
        publish = datetime(2026, 1, 14, 6, tzinfo=timezone.utc)
        rows = [
            windfor_row(
                publish_time=publish,
                start_time=datetime(2026, 1, 14, 21, tzinfo=timezone.utc) + timedelta(hours=i),
                generation=100 + i,
            )
            for i in range(3)
        ]
        service = IngestionService(session_factory, FakeClient(rows))
        service.ingest_forecasts(publish, publish + timedelta(hours=6))
        service.ingest_forecasts(publish, publish + timedelta(hours=6))
        with session_factory() as db:
            assert db.scalar(select(ForecastVintage).where(ForecastVintage.publish_time_utc == publish)) is not None
            assert len(db.scalars(select(ForecastVintage)).all()) == 1


def ActualRows(db):  # noqa: N802 - tiny helper used as a callable
    from sqlalchemy import func

    from app.models.actual import ActualGeneration

    return db.scalars(select(ActualGeneration)).all()


class TestSelectionRebuild:
    def test_look_ahead_bias_cannot_occur(self, session_factory) -> None:
        """A vintage published after the cutoff must never appear in a selection."""
        with session_factory() as db:
            start = datetime(2026, 1, 15, 0, tzinfo=timezone.utc)
            eligible = add_vintage(
                db,
                publish_time_utc=CUTOFF - timedelta(minutes=20),
                points=hourly_points(start, 48, Decimal("1000")),
            )
            late = add_vintage(
                db,
                publish_time_utc=CUTOFF + timedelta(minutes=30),
                points=hourly_points(start, 48, Decimal("9999")),
            )
            db.commit()
            eligible_id, late_id = eligible.id, late.id

            summary = ForecastSelectionService(db).rebuild(DAY, DAY)
            db.commit()

            assert summary.intervals == 48
            assert summary.selected == 48

            rows = ForecastSelectionRepository(db).fetch_day_selections(
                policy_id=CutoffPolicyRepository(db).get_default().id, delivery_date=DAY
            )
            assert len(rows) == 48
            assert all(row.vintage_id == eligible_id for row in rows)
            assert all(row.vintage_id != late_id for row in rows)
            assert all(row.forecast_mw == Decimal("1000") for row in rows)
            assert all(row.cutoff_utc == CUTOFF for row in rows)
            assert all(row.vintage_publish_time_utc <= CUTOFF for row in rows)
            assert all((row.lead_time_minutes or 0) > 0 for row in rows)

    def test_days_without_vintages_are_reported_not_filled(self, session_factory) -> None:
        with session_factory() as db:
            summary = ForecastSelectionService(db).rebuild(DAY, DAY)
            db.commit()

            assert summary.selected == 0
            assert summary.no_vintage_before_cutoff == 48
            assert DAY.isoformat() in summary.missing_days

            rows = ForecastSelectionRepository(db).fetch_day_selections(
                policy_id=CutoffPolicyRepository(db).get_default().id, delivery_date=DAY
            )
            assert all(row.forecast_mw is None for row in rows)
            assert all(row.vintage_id is None for row in rows)

            issues = db.scalars(select(DataQualityIssue)).all()
            assert any(issue.issue_type == "NO_VINTAGE_BEFORE_CUTOFF" for issue in issues)

    def test_fallback_is_used_when_the_newest_vintage_lacks_the_hour(
        self, session_factory
    ) -> None:
        with session_factory() as db:
            broad = add_vintage(
                db,
                publish_time_utc=CUTOFF - timedelta(hours=6),
                points=hourly_points(
                    datetime(2026, 1, 15, 0, tzinfo=timezone.utc), 48, Decimal("800")
                ),
            )
            # The freshest eligible vintage carries a single mid-day hour, so it
            # genuinely does not cover the last period and a fallback must happen.
            narrow_start = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
            add_vintage(
                db,
                publish_time_utc=CUTOFF - timedelta(minutes=5),
                points={narrow_start: Decimal("1234")},
            )
            db.commit()

            ForecastSelectionService(db).rebuild(DAY, DAY)
            db.commit()

            rows = ForecastSelectionRepository(db).fetch_day_selections(
                policy_id=CutoffPolicyRepository(db).get_default().id, delivery_date=DAY
            )
            last = rows[-1]
            assert last.vintage_id == broad.id
            assert last.fallback_depth == 1
            assert last.forecast_mw == Decimal("800")

    def test_later_cutoff_policy_sees_fresher_vintages(self, session_factory) -> None:
        with session_factory() as db:
            start = datetime(2026, 1, 15, 0, tzinfo=timezone.utc)
            add_vintage(
                db,
                publish_time_utc=datetime(2026, 1, 14, 8, tzinfo=timezone.utc),
                points=hourly_points(start, 48, Decimal("500")),
            )
            fresher = add_vintage(
                db,
                publish_time_utc=datetime(2026, 1, 14, 14, tzinfo=timezone.utc),
                points=hourly_points(start, 48, Decimal("700")),
            )
            db.commit()

            early = ForecastSelectionService(db).rebuild(DAY, DAY, policy_code="EPEX_GB_DA_1H_0920")
            late = ForecastSelectionService(db).rebuild(DAY, DAY, policy_code="EPEX_GB_DA_30M_1530")
            db.commit()

            assert early.selected == 48 and late.selected == 48
            late_rows = ForecastSelectionRepository(db).fetch_day_selections(
                policy_id=CutoffPolicyRepository(db).get_by_code("EPEX_GB_DA_30M_1530").id,
                delivery_date=DAY,
            )
            assert all(row.vintage_id == fresher.id for row in late_rows)
            assert all(row.forecast_mw == Decimal("700") for row in late_rows)

    def test_coverage_view_reflects_selections(self, session_factory) -> None:
        with session_factory() as db:
            add_vintage(
                db,
                publish_time_utc=CUTOFF - timedelta(hours=1),
                points=hourly_points(
                    datetime(2026, 1, 15, 0, tzinfo=timezone.utc), 48, Decimal("900")
                ),
            )
            db.commit()
            ForecastSelectionService(db).rebuild(DAY, DAY)
            db.commit()

            policy = CutoffPolicyRepository(db).get_default()
            coverage = DataStatusRepository(db).coverage(policy.id, DAY, DAY)
            assert len(coverage) == 1
            assert coverage[0].intervals == 48
            assert coverage[0].selected_intervals == 48
            assert coverage[0].missing_intervals == 0


class TestJanuaryDecisionWindow:
    """A January decision must be able to deliver on 1 February."""

    def test_first_february_delivery_uses_only_january_vintages_before_cutoff(
        self, session_factory
    ) -> None:
        february_first = date(2026, 2, 1)
        horizon = datetime(2026, 1, 31, 21, tzinfo=timezone.utc)
        before_cutoff = datetime(2026, 1, 31, 7, 30, tzinfo=timezone.utc)
        after_cutoff = datetime(2026, 1, 31, 9, 30, tzinfo=timezone.utc)

        with session_factory() as db:
            policy = CutoffPolicyRepository(db).get_default()
            add_vintage(
                db,
                publish_time_utc=before_cutoff,
                points=hourly_points(horizon, 73, Decimal("5000")),
            )
            add_vintage(
                db,
                publish_time_utc=after_cutoff,
                points=hourly_points(horizon, 73, Decimal("99999")),
            )
            db.commit()

            summary = ForecastSelectionService(db).rebuild(february_first, february_first)
            db.commit()

            assert summary.cutoff_definition == "09:20 Europe/London on delivery_date-1 day"
            assert summary.intervals == 48
            assert summary.selected == 48
            assert summary.no_vintage_before_cutoff == 0
            # The 09:30 vintage is after the 31 Jan 09:20 cutoff, so only one
            # vintage is even considered for this delivery day.
            assert summary.vintages_considered == 1
            assert summary.min_lead_minutes == 990
            assert summary.max_lead_minutes == 2400

            rows = ForecastSelectionRepository(db).fetch_day_selections(
                policy_id=policy.id, delivery_date=february_first
            )
            assert len(rows) == 48
            assert all(
                row.cutoff_utc == datetime(2026, 1, 31, 9, 20, tzinfo=timezone.utc)
                for row in rows
            )
            assert all(row.vintage_publish_time_utc == before_cutoff for row in rows)
            assert all(row.forecast_mw == Decimal("5000") for row in rows)
            assert all(row.lead_time_minutes >= 0 for row in rows)

            # The post-cutoff publication remains stored and auditable.
            stored = db.scalars(select(ForecastVintage)).all()
            assert len(stored) == 2
