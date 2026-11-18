"""Repository behaviour against a real MySQL 8 test database."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.integrations.elexon.actuals import NormalisedActual
from app.integrations.elexon.forecasts import NormalisedPoint, NormalisedVintage
from app.repositories.actual_generation_repository import ActualGenerationRepository
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.forecast_selection_repository import (
    ForecastSelectionRepository,
    SelectionRow,
)
from app.repositories.forecast_vintage_repository import ForecastVintageRepository
from app.repositories.ingestion_run_repository import IngestionRunRepository, RunCounts
from app.models.forecast import ForecastPoint

DAY = date(2026, 1, 15)
PUBLISH = datetime(2026, 1, 14, 9, 0, tzinfo=timezone.utc)


def _vintage(points: dict[datetime, Decimal | None]) -> NormalisedVintage:
    starts = sorted(points)
    return NormalisedVintage(
        publish_time_utc=PUBLISH,
        resolution_minutes=60,
        points=[
            NormalisedPoint(
                valid_from_utc=start,
                valid_to_utc=start + timedelta(hours=1),
                generation_mw=points[start],
            )
            for start in starts
        ],
        source_row_count=len(starts),
    )


class TestVintagePersistence:
    def test_upsert_is_idempotent(self, session) -> None:
        repo = ForecastVintageRepository(session)
        points = {
            datetime(2026, 1, 15, 0, tzinfo=timezone.utc): Decimal("1000"),
            datetime(2026, 1, 15, 1, tzinfo=timezone.utc): Decimal("1100"),
        }
        first = repo.upsert_vintage(_vintage(points), run_id=None)
        session.commit()
        second = repo.upsert_vintage(_vintage(points), run_id=None)
        session.commit()

        assert first.created is True
        assert first.points_inserted == 2
        assert second.created is False
        assert second.points_inserted == 0
        assert second.points_unchanged == 2
        assert session.query(ForecastPoint).count() == 2

    def test_revised_value_is_updated_and_reported(self, session) -> None:
        repo = ForecastVintageRepository(session)
        moment = datetime(2026, 1, 15, 0, tzinfo=timezone.utc)
        repo.upsert_vintage(_vintage({moment: Decimal("1000")}), run_id=None)
        session.commit()

        result = repo.upsert_vintage(_vintage({moment: Decimal("1200")}), run_id=None)
        session.commit()

        assert result.points_updated == 1
        assert result.revisions[0][1] == Decimal("1000")
        assert result.revisions[0][2] == Decimal("1200")
        stored = session.query(ForecastPoint).one()
        assert stored.generation_mw == Decimal("1200")

    def test_point_requires_an_existing_vintage(self, session) -> None:
        session.add(
            ForecastPoint(
                vintage_id=999_999,
                valid_from_utc=datetime(2026, 1, 15, tzinfo=timezone.utc),
                valid_to_utc=datetime(2026, 1, 15, 1, tzinfo=timezone.utc),
                generation_mw=Decimal("1"),
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_duplicate_publish_time_is_rejected_by_the_database(self, session) -> None:
        from app.models.forecast import ForecastVintage

        for _ in range(2):
            session.add(
                ForecastVintage(
                    dataset="WINDFOR",
                    publish_time_utc=PUBLISH,
                    horizon_start_utc=PUBLISH,
                    horizon_end_utc=PUBLISH + timedelta(hours=1),
                    resolution_minutes=60,
                    point_count=1,
                )
            )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


class TestActualPersistence:
    def _row(self, period: int, mw: Decimal | None, publish: datetime) -> NormalisedActual:
        start = datetime(2026, 1, 15, tzinfo=timezone.utc) + timedelta(minutes=30 * (period - 1))
        return NormalisedActual(
            settlement_date=DAY,
            settlement_period=period,
            start_time_utc=start,
            end_time_utc=start + timedelta(minutes=30),
            generation_mw=mw,
            publish_time_utc=publish,
        )

    def test_upsert_is_idempotent(self, session) -> None:
        repo = ActualGenerationRepository(session)
        publish = datetime(2026, 1, 15, 1, tzinfo=timezone.utc)
        rows = [self._row(1, Decimal("1000"), publish)]
        first = repo.upsert_many(rows, run_id=None)
        session.commit()
        second = repo.upsert_many(rows, run_id=None)
        session.commit()
        assert first.inserted == 1
        assert second.inserted == 0
        assert second.unchanged == 1

    def test_revision_keeps_history_and_view_returns_latest(self, session) -> None:
        repo = ActualGenerationRepository(session)
        original = datetime(2026, 1, 15, 1, tzinfo=timezone.utc)
        revised = original + timedelta(hours=3)
        repo.upsert_many([self._row(1, Decimal("1000"), original)], run_id=None)
        repo.upsert_many([self._row(1, Decimal("900"), revised)], run_id=None)
        session.commit()

        assert repo.revision_count() == 2
        latest = repo.latest_for_range(DAY, DAY)
        assert len(latest) == 1
        assert latest[0].generation_mw == Decimal("900")
        assert latest[0].source_publish_time_utc == revised

    def test_null_generation_is_stored_as_null(self, session) -> None:
        repo = ActualGenerationRepository(session)
        publish = datetime(2026, 1, 15, 1, tzinfo=timezone.utc)
        repo.upsert_many([self._row(2, None, publish)], run_id=None)
        session.commit()
        latest = repo.latest_for_range(DAY, DAY)
        assert latest[0].generation_mw is None


class TestSelectionsAndRuns:
    def test_selection_replace_range_is_idempotent(self, session) -> None:
        repo = ForecastSelectionRepository(session)
        policy = CutoffPolicyRepository(session).get_default()
        rows = [
            SelectionRow(
                settlement_date=DAY,
                settlement_period=1,
                interval_start_utc=datetime(2026, 1, 15, tzinfo=timezone.utc),
                cutoff_utc=datetime(2026, 1, 14, 9, 20, tzinfo=timezone.utc),
                vintage_id=None,
                vintage_publish_time_utc=None,
                lead_time_minutes=None,
                forecast_mw=None,
                fallback_depth=0,
                selection_status="no_vintage_before_cutoff",
            )
        ]
        repo.replace_range(policy_id=policy.id, date_from=DAY, date_to=DAY, rows=rows)
        session.commit()
        repo.replace_range(policy_id=policy.id, date_from=DAY, date_to=DAY, rows=rows)
        session.commit()
        assert repo.count_range(policy.id, DAY, DAY) == 1

    def test_run_lifecycle_and_watermark(self, session) -> None:
        repo = IngestionRunRepository(session)
        run = repo.create(
            dataset="FUELHH",
            run_type="manual",
            window_from=datetime(2026, 1, 15, tzinfo=timezone.utc),
            window_to=datetime(2026, 1, 16, tzinfo=timezone.utc),
        )
        session.commit()
        repo.finish(
            run.id,
            status="succeeded",
            counts=RunCounts(rows_fetched=48, rows_inserted=48, http_requests=1, http_status=200),
        )
        repo.set_watermark("FUELHH", run.id, datetime(2026, 1, 16, tzinfo=timezone.utc))
        session.commit()

        stored = repo.get(run.id)
        assert stored is not None
        assert stored.status == "succeeded"
        assert stored.rows_inserted == 48
        assert stored.finished_at_utc is not None
        watermark = repo.get_watermark("FUELHH")
        assert watermark is not None
        assert watermark.last_success_to_utc == datetime(2026, 1, 16, tzinfo=timezone.utc)

    def test_watermark_never_moves_backwards(self, session) -> None:
        repo = IngestionRunRepository(session)
        run = repo.create(
            dataset="WINDFOR",
            run_type="manual",
            window_from=datetime(2026, 1, 15, tzinfo=timezone.utc),
            window_to=datetime(2026, 1, 16, tzinfo=timezone.utc),
        )
        session.commit()
        repo.set_watermark("WINDFOR", run.id, datetime(2026, 1, 16, tzinfo=timezone.utc))
        session.commit()
        repo.set_watermark("WINDFOR", run.id, datetime(2026, 1, 10, tzinfo=timezone.utc))
        session.commit()
        assert repo.get_watermark("WINDFOR").last_success_to_utc == datetime(
            2026, 1, 16, tzinfo=timezone.utc
        )

    def test_unknown_policy_code_is_a_404(self, session) -> None:
        from app.core.errors import NotFoundError

        with pytest.raises(NotFoundError):
            CutoffPolicyRepository(session).get_by_code("DOES_NOT_EXIST")
