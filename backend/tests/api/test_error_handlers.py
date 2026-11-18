"""Error-handler regression tests.

These exist because a logging quirk once turned every 5xx domain error and every
Elexon failure into a generic HTTP 500: ``logging`` raises
``KeyError: Attempt to overwrite 'message' in LogRecord`` when a record carries a
``message`` extra, and the handler itself then failed.

Each test therefore asserts both the status code **and** the error code, so a
handler that throws while handling an exception cannot pass silently.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.core.errors import AppError
from app.integrations.elexon.errors import ElexonRequestError, ElexonSchemaError
from app.main import create_app
from app.core.config import Settings


class _TeapotError(AppError):
    """A 5xx domain error, the class of error whose logging path broke."""

    code = "TEAPOT_FAILURE"
    status_code = 503


def _client_raising(exc: Exception) -> TestClient:
    """Build a throwaway app whose only route raises ``exc``."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:  # pragma: no cover - always raises
        raise exc

    return TestClient(app, raise_server_exceptions=False)


def test_5xx_domain_error_keeps_its_status_and_code() -> None:
    response = _client_raising(_TeapotError("service is disabled")).get("/boom")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "TEAPOT_FAILURE"
    assert body["error"]["message"] == "service is disabled"


def test_upstream_transport_error_maps_to_502() -> None:
    response = _client_raising(
        ElexonRequestError("connection reset", http_status=None)
    ).get("/boom")
    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "ELEXON_TRANSPORT_ERROR"
    assert "Elexon request failed" in body["error"]["message"]


def test_upstream_schema_error_maps_to_502_with_status() -> None:
    response = _client_raising(
        ElexonSchemaError("unexpected payload", http_status=200)
    ).get("/boom")
    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "ELEXON_SCHEMA_ERROR"
    assert body["error"]["details"]["http_status"] == 200


def test_admin_endpoints_answer_503_when_no_token_is_configured() -> None:
    """Disabled administration must be a clear 503, not a generic 500."""
    app = create_app(Settings(admin_token=None, environment="test"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/admin/selections/rebuild",
            params={"from": "2026-01-15", "to": "2026-01-15"},
        )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "ADMIN_DISABLED"
    assert "ADMIN_TOKEN" in body["error"]["message"]
