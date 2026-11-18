"""HTTP contract tests against a real MySQL test database."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.services.forecast_selection_service import ForecastSelectionService
from tests.fixtures.builders import add_actual, add_vintage, hourly_points

API = "/api/v1"
DAY = date(2026, 1, 15)
CUTOFF = datetime(2026, 1, 14, 9, 20, tzinfo=timezone.utc)
ADMIN_HEADERS = {"X-Admin-Token": "test-admin-token"}


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.fixture
def seeded(session_factory):  # noqa: ANN001, ANN201
    """One delivery day: two vintages, 48 actuals, selections built."""
    with session_factory() as db:
        # A 48-hour horizon starting at the first hour of the delivery day, so the
        # fixture covers every settlement period of that day (00:00-23:00).
        start = datetime(2026, 1, 15, 0, tzinfo=timezone.utc)
        add_vintage(
            db,
            publish_time_utc=CUTOFF - timedelta(hours=2),
            points=hourly_points(start, 48, Decimal("1000")),
        )
        add_vintage(
            db,
            publish_time_utc=CUTOFF + timedelta(hours=4),
            points=hourly_points(start, 48, Decimal("2000")),
        )
        for period in range(1, 49):
            add_actual(
                db,
                settlement_date=DAY,
                settlement_period=period,
                generation_mw=Decimal("900"),
            )
        db.commit()
        ForecastSelectionService(db).rebuild(DAY, DAY)
        db.commit()
    return DAY


class TestHealthAndMeta:
    def test_health(self, client) -> None:
        response = client.get(f"{API}/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == "0.2.0"

    def test_readiness_reports_migration_revision(self, client) -> None:
        response = client.get(f"{API}/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["database"] == "ok"
        assert body["alembic_revision"] is not None

    def test_meta_config(self, client) -> None:
        response = client.get(f"{API}/meta/config")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["timezone_storage"] == "UTC"
        assert data["timezone_display"] == "Europe/London"
        assert data["default_cutoff_policy"] == "EPEX_GB_DA_1H_0920"
        assert len(data["cutoff_policies"]) == 3
        assert "illustrative" in data["disclaimers"]["procurement"].lower()
        assert data["windfor_sp_mapping"] in ("step", "linear")

    def test_openapi_schema_is_served(self, client) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "/api/v1/analysis/accuracy" in response.json()["paths"]


class TestActuals:
    def test_list_actuals(self, client, seeded) -> None:
        response = client.get(f"{API}/actuals", params={"from": DAY.isoformat(), "to": DAY.isoformat()})
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 48
        assert body["meta"]["pagination"]["total"] == 48
        first = body["data"][0]
        assert first["settlement_period"] == 1
        assert first["generation_mw"] == 900.0
        assert "GMT" in first["local_start"] or "BST" in first["local_start"]

    def test_daily_actuals(self, client, seeded) -> None:
        response = client.get(
            f"{API}/actuals/daily", params={"from": DAY.isoformat(), "to": DAY.isoformat()}
        )
        assert response.status_code == 200
        row = response.json()["data"][0]
        assert row["periods_with_data"] == 48
        assert row["mean_mw"] == pytest.approx(900.0)
        assert row["total_mwh"] == pytest.approx(48 * 900 * 0.5)

    def test_pagination_is_applied(self, client, seeded) -> None:
        response = client.get(
            f"{API}/actuals",
            params={"from": DAY.isoformat(), "to": DAY.isoformat(), "limit": 10, "offset": 5},
        )
        body = response.json()
        assert len(body["data"]) == 10
        assert body["data"][0]["settlement_period"] == 6
        assert body["meta"]["pagination"]["returned"] == 10

    def test_inverted_range_is_rejected(self, client) -> None:
        response = client.get(f"{API}/actuals", params={"from": "2026-02-01", "to": "2026-01-01"})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_REQUEST"

    def test_oversized_page_is_rejected(self, client) -> None:
        response = client.get(
            f"{API}/actuals",
            params={"from": DAY.isoformat(), "to": DAY.isoformat(), "limit": 6000},
        )
        assert response.status_code == 422


class TestForecastEndpoints:
    def test_selection_missing_is_409(self, client) -> None:
        response = client.get(f"{API}/forecast/latest", params={"delivery_date": DAY.isoformat()})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DATA_UNAVAILABLE"

    def test_selected_day_uses_the_eligible_vintage(self, client, seeded) -> None:
        response = client.get(f"{API}/forecast/latest", params={"delivery_date": DAY.isoformat()})
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["intervals"]) == 48
        assert data["summary"]["selected"] == 48
        assert data["summary"]["missing"] == 0
        assert _parse(data["cutoff_utc"]) == CUTOFF
        for interval in data["intervals"]:
            assert interval["forecast_mw"] == 1000.0
            assert interval["selection_status"] == "selected"
            assert _parse(interval["vintage_publish_time_utc"]) <= CUTOFF
            assert interval["lead_time_minutes"] > 0

    def test_vintage_lineage_flags_after_cutoff(self, client, seeded) -> None:
        response = client.get(f"{API}/forecast/vintages", params={"delivery_date": DAY.isoformat()})
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["vintages"]) == 2
        after = [v for v in data["vintages"] if v["is_after_cutoff"]]
        used = [v for v in data["vintages"] if v["is_used_at_cutoff"]]
        assert len(after) == 1
        assert len(used) == 1
        assert after[0]["vintage_id"] != used[0]["vintage_id"]
        assert used[0]["hours_in_delivery_day"] == 24

    def test_vintage_detail_and_404(self, client, seeded) -> None:
        lineage = client.get(
            f"{API}/forecast/vintages", params={"delivery_date": DAY.isoformat()}
        ).json()["data"]
        vintage_id = lineage["vintages"][0]["vintage_id"]

        response = client.get(f"{API}/forecast/vintages/{vintage_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["resolution_minutes"] == 60
        assert data["point_count"] == 48
        assert len(data["points"]) == 48

        missing = client.get(f"{API}/forecast/vintages/999999")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "NOT_FOUND"

    def test_unknown_cutoff_policy_is_404(self, client, seeded) -> None:
        response = client.get(
            f"{API}/forecast/latest",
            params={"delivery_date": DAY.isoformat(), "cutoff_policy": "NOPE"},
        )
        assert response.status_code == 404


class TestAccuracy:
    def test_summary(self, client, seeded) -> None:
        response = client.get(
            f"{API}/analysis/accuracy", params={"from": DAY.isoformat(), "to": DAY.isoformat()}
        )
        assert response.status_code == 200
        metrics = response.json()["data"]["metrics"]
        assert metrics["n_evaluated"] == 48
        assert metrics["n_expected"] == 48
        assert metrics["mae_mw"] == pytest.approx(100.0)
        assert metrics["rmse_mw"] == pytest.approx(100.0)
        assert metrics["bias_mw"] == pytest.approx(100.0)
        assert metrics["wape_pct"] == pytest.approx(11.111, abs=1e-3)
        assert metrics["coverage_pct"] == pytest.approx(100.0)
        assert metrics["insufficient_data"] is False

    def test_daily(self, client, seeded) -> None:
        response = client.get(
            f"{API}/analysis/accuracy/daily",
            params={"from": DAY.isoformat(), "to": DAY.isoformat()},
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert len(rows) == 1
        assert rows[0]["settlement_date"] == DAY.isoformat()
        assert rows[0]["accuracy_pct"] == pytest.approx(88.889, abs=1e-3)

    def test_by_lead_time_covers_every_bucket(self, client, seeded) -> None:
        response = client.get(
            f"{API}/analysis/accuracy/by-lead-time",
            params={"from": DAY.isoformat(), "to": DAY.isoformat()},
        )
        assert response.status_code == 200
        buckets = response.json()["data"]
        assert [bucket["label"] for bucket in buckets] == [
            "0-6h",
            "6-12h",
            "12-18h",
            "18-24h",
            "24-36h",
            "36-48h",
            ">48h",
            "unknown",
        ]
        assert sum(bucket["metrics"]["n_evaluated"] for bucket in buckets) == 48
        assert all(bucket["is_empty"] for bucket in buckets if bucket["label"] in (">48h", "unknown"))

    def test_hourly_granularity_halves_the_sample(self, client, seeded) -> None:
        response = client.get(
            f"{API}/analysis/accuracy",
            params={
                "from": DAY.isoformat(),
                "to": DAY.isoformat(),
                "granularity": "hourly",
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["metrics"]["n_evaluated"] == 24

    def test_empty_range_reports_insufficient_data(self, client) -> None:
        response = client.get(
            f"{API}/analysis/accuracy",
            params={"from": "2026-02-01", "to": "2026-02-02"},
        )
        assert response.status_code == 200
        metrics = response.json()["data"]["metrics"]
        assert metrics["insufficient_data"] is True
        assert metrics["n_evaluated"] == 0
        assert metrics["mae_mw"] is None


class TestProcurement:
    def test_shortfall_calculation(self, client, seeded) -> None:
        response = client.post(
            f"{API}/procurement/scenario",
            json={
                "demand_mw": 2000,
                "date_from": DAY.isoformat(),
                "date_to": DAY.isoformat(),
            },
        )
        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        assert data["totals"]["intervals"] == 48
        assert data["totals"]["shortfall_intervals"] == 48
        assert data["totals"]["total_delta_mwh"] == pytest.approx(48 * 1000 * 0.5)
        assert data["totals"]["shortfall_mwh"] == pytest.approx(24_000)
        assert data["totals"]["unavailable_intervals"] == 0
        assert data["intervals"][0]["delta_mw"] == pytest.approx(1000.0)
        assert data["intervals"][0]["classification"] == "shortfall"
        assert "Illustrative estimate only" in data["disclaimer"]
        assert body["meta"]["kind"] == "illustrative_estimate"

    def test_negative_demand_is_rejected(self, client) -> None:
        response = client.post(
            f"{API}/procurement/scenario",
            json={"demand_mw": -1, "date_from": DAY.isoformat(), "date_to": DAY.isoformat()},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_without_intervals(self, client, seeded) -> None:
        response = client.post(
            f"{API}/procurement/scenario",
            json={
                "demand_mw": 2000,
                "date_from": DAY.isoformat(),
                "date_to": DAY.isoformat(),
                "include_intervals": False,
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["intervals"] == []


class TestDataStatus:
    def test_status(self, client, seeded) -> None:
        response = client.get(
            f"{API}/data/status", params={"from": DAY.isoformat(), "to": DAY.isoformat()}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["selection_intervals"] == 48
        assert data["forecast_vintages"] == 2
        assert data["actual_settlement_periods"] == 48
        assert len(data["coverage"]) == 1
        assert data["coverage"][0]["missing_intervals"] == 0
        assert data["policy_code"] == "EPEX_GB_DA_1H_0920"

    def test_runs_and_issues_are_lists(self, client) -> None:
        runs = client.get(f"{API}/data/runs")
        issues = client.get(f"{API}/data/issues")
        assert runs.status_code == 200
        assert issues.status_code == 200
        assert isinstance(runs.json()["data"], list)
        assert isinstance(issues.json()["data"], list)

    def test_invalid_dataset_filter_is_422(self, client) -> None:
        assert client.get(f"{API}/data/runs", params={"dataset": "NOPE"}).status_code == 422


class TestAdministration:
    def test_missing_token_is_401(self, client) -> None:
        response = client.post(
            f"{API}/admin/selections/rebuild",
            params={"from": DAY.isoformat(), "to": DAY.isoformat()},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

    def test_wrong_token_is_401(self, client) -> None:
        response = client.post(
            f"{API}/admin/selections/rebuild",
            params={"from": DAY.isoformat(), "to": DAY.isoformat()},
            headers={"X-Admin-Token": "wrong"},
        )
        assert response.status_code == 401

    def test_rebuild_with_token(self, client, seeded) -> None:
        response = client.post(
            f"{API}/admin/selections/rebuild",
            params={"from": DAY.isoformat(), "to": DAY.isoformat()},
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["intervals"] == 48
        assert data["selected"] == 48


class TestCorsAndErrors:
    def test_cors_preflight_for_configured_origin(self, client) -> None:
        response = client.options(
            f"{API}/actuals",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_unlisted_origin_is_not_allowed(self, client) -> None:
        response = client.get(f"{API}/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in response.headers

    def test_unknown_route_returns_404(self, client) -> None:
        assert client.get(f"{API}/does-not-exist").status_code == 404
