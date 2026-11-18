"""Normalisation of FUELHH and WINDFOR payloads.

The ``FakeClient`` stands in for the HTTP client and returns hand-written rows,
so these tests never touch the network and never use "real" data as fixtures.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.integrations.elexon.actuals import fetch_wind_actuals
from app.integrations.elexon.errors import ElexonSchemaError
from app.integrations.elexon.forecasts import fetch_forecast_vintages
from tests.fixtures.builders import fuelhh_row, windfor_row


class FakeClient:
    """Minimal stand-in for ``ElexonClient``."""

    def __init__(self, rows: list[dict[str, object]], status: int = 200) -> None:
        self.rows = rows
        self.last_status = status
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_rows(self, path: str, params: dict[str, object]) -> list[dict[str, object]]:
        self.calls.append((path, params))
        return self.rows


DAY = date(2026, 1, 15)


class TestActualsNormalisation:
    def test_rows_are_mapped_to_settlement_periods(self) -> None:
        client = FakeClient(
            [fuelhh_row(settlement_date=DAY, settlement_period=1, generation=10000)]
        )
        result = fetch_wind_actuals(client, DAY, DAY)
        assert result.requests == 1
        assert len(result.rows) == 1
        row = result.rows[0]
        assert (row.settlement_date, row.settlement_period) == (DAY, 1)
        assert row.start_time_utc == datetime(2026, 1, 15, tzinfo=timezone.utc)
        assert row.generation_mw == Decimal("10000")
        assert client.calls[0][0] == "/datasets/FUELHH/stream"
        assert client.calls[0][1]["fuelType"] == "WIND"

    def test_null_generation_is_preserved(self) -> None:
        client = FakeClient([fuelhh_row(settlement_date=DAY, settlement_period=2, generation=None)])
        result = fetch_wind_actuals(client, DAY, DAY)
        assert result.rows[0].generation_mw is None
        assert result.rejected == []

    def test_non_wind_rows_are_rejected(self) -> None:
        row = fuelhh_row(settlement_date=DAY, settlement_period=1, generation=1)
        row["fuelType"] = "SOLAR"
        result = fetch_wind_actuals(FakeClient([row]), DAY, DAY)
        assert result.rows == []
        assert result.rejected[0].reason == "unexpected_fuel_type"

    def test_settlement_period_mismatch_is_rejected(self) -> None:
        row = fuelhh_row(settlement_date=DAY, settlement_period=5, generation=1)
        row["settlementPeriod"] = 6
        result = fetch_wind_actuals(FakeClient([row]), DAY, DAY)
        assert result.rows == []
        assert result.rejected[0].reason == "settlement_period_mismatch"

    def test_settlement_date_mismatch_is_rejected(self) -> None:
        row = fuelhh_row(settlement_date=DAY, settlement_period=1, generation=1)
        row["settlementDate"] = "2026-01-16"
        result = fetch_wind_actuals(FakeClient([row]), DAY, DAY)
        assert result.rejected[0].reason == "settlement_date_mismatch"

    def test_duplicate_rows_are_collapsed_and_reported(self) -> None:
        row = fuelhh_row(settlement_date=DAY, settlement_period=3, generation=500)
        result = fetch_wind_actuals(FakeClient([row, dict(row)]), DAY, DAY)
        assert len(result.rows) == 1
        assert result.rejected[0].reason == "duplicate_in_payload"

    def test_rows_outside_the_requested_window_are_rejected(self) -> None:
        row = fuelhh_row(settlement_date=date(2026, 1, 20), settlement_period=1, generation=1)
        result = fetch_wind_actuals(FakeClient([row]), DAY, DAY)
        assert result.rows == []
        assert result.rejected[0].reason == "outside_requested_window"

    def test_malformed_row_raises_schema_error(self) -> None:
        client = FakeClient([{"dataset": "FUELHH", "fuelType": "WIND"}])
        with pytest.raises(ElexonSchemaError):
            fetch_wind_actuals(client, DAY, DAY)


PUBLISH = datetime(2026, 1, 14, 9, 30, tzinfo=timezone.utc)


def _forecast_rows(publish: datetime, start: datetime, count: int, value: int = 1000):
    return [
        windfor_row(
            publish_time=publish,
            start_time=datetime.fromtimestamp(start.timestamp() + 3600 * index, tz=timezone.utc),
            generation=value,
        )
        for index in range(count)
    ]


class TestForecastNormalisation:
    def test_rows_are_grouped_into_vintages(self) -> None:
        client = FakeClient(
            _forecast_rows(PUBLISH, datetime(2026, 1, 14, 21, tzinfo=timezone.utc), 3)
        )
        result = fetch_forecast_vintages(client, PUBLISH, PUBLISH.replace(hour=12))
        assert len(result.vintages) == 1
        vintage = result.vintages[0]
        assert vintage.resolution_minutes == 60
        assert len(vintage.points) == 3
        assert vintage.horizon_start_utc == datetime(2026, 1, 14, 21, tzinfo=timezone.utc)
        assert vintage.horizon_end_utc == datetime(2026, 1, 15, 0, tzinfo=timezone.utc)
        assert client.calls[0][0] == "/datasets/WINDFOR/stream"

    def test_two_publications_become_two_vintages(self) -> None:
        second = PUBLISH.replace(hour=11, minute=30)
        rows = _forecast_rows(PUBLISH, datetime(2026, 1, 14, 21, tzinfo=timezone.utc), 2)
        rows += _forecast_rows(second, datetime(2026, 1, 15, 0, tzinfo=timezone.utc), 2, value=900)
        result = fetch_forecast_vintages(FakeClient(rows), PUBLISH, PUBLISH.replace(hour=18))
        assert [v.publish_time_utc for v in result.vintages] == [PUBLISH, second]

    def test_null_generation_is_preserved(self) -> None:
        rows = [windfor_row(publish_time=PUBLISH, start_time=datetime(2026, 1, 14, 21, tzinfo=timezone.utc), generation=None)]
        rows.append(
            windfor_row(
                publish_time=PUBLISH,
                start_time=datetime(2026, 1, 14, 22, tzinfo=timezone.utc),
                generation=500,
            )
        )
        result = fetch_forecast_vintages(FakeClient(rows), PUBLISH, PUBLISH.replace(hour=12))
        assert result.vintages[0].points[0].generation_mw is None

    def test_rows_outside_the_publish_window_are_rejected(self) -> None:
        rows = _forecast_rows(PUBLISH, datetime(2026, 1, 14, 21, tzinfo=timezone.utc), 2)
        result = fetch_forecast_vintages(
            FakeClient(rows), PUBLISH + __import__("datetime").timedelta(hours=1), PUBLISH + __import__("datetime").timedelta(hours=2)
        )
        assert result.vintages == []
        assert result.rejected[0].reason == "outside_requested_window"

    def test_off_grid_point_is_rejected(self) -> None:
        base = datetime(2026, 1, 14, 21, tzinfo=timezone.utc)
        rows = [
            windfor_row(publish_time=PUBLISH, start_time=base, generation=100),
            windfor_row(
                publish_time=PUBLISH,
                start_time=base.replace(hour=22),
                generation=110,
            ),
            windfor_row(
                publish_time=PUBLISH,
                start_time=base.replace(hour=22, minute=20),
                generation=120,
            ),
        ]
        result = fetch_forecast_vintages(FakeClient(rows), PUBLISH, PUBLISH.replace(hour=12))
        assert len(result.vintages[0].points) == 2
        assert any(rejected.reason == "off_grid_point" for rejected in result.rejected)

    def test_single_point_vintage_is_rejected(self) -> None:
        rows = [windfor_row(publish_time=PUBLISH, start_time=datetime(2026, 1, 14, 21, tzinfo=timezone.utc), generation=1)]
        result = fetch_forecast_vintages(FakeClient(rows), PUBLISH, PUBLISH.replace(hour=12))
        assert result.vintages == []
        assert result.rejected[0].reason == "single_point_vintage"

    def test_duplicate_start_time_is_collapsed_and_reported(self) -> None:
        base = datetime(2026, 1, 14, 21, tzinfo=timezone.utc)
        rows = [
            windfor_row(publish_time=PUBLISH, start_time=base, generation=100),
            windfor_row(publish_time=PUBLISH, start_time=base, generation=105),
            windfor_row(publish_time=PUBLISH, start_time=base.replace(hour=22), generation=110),
        ]
        result = fetch_forecast_vintages(FakeClient(rows), PUBLISH, PUBLISH.replace(hour=12))
        assert len(result.vintages[0].points) == 2
        assert any(rejected.reason == "duplicate_in_payload" for rejected in result.rejected)
