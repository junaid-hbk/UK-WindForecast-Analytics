"""Elexon HTTP client behaviour: retries, status handling, payload shapes.

No test contacts the live API; every response comes from an in-process
``httpx.MockTransport``.
"""

from __future__ import annotations

import httpx
import pytest

from app.integrations.elexon.client import ElexonClient, backoff_delay
from app.integrations.elexon.errors import (
    ElexonHTTPError,
    ElexonParameterError,
    ElexonRequestError,
    ElexonSchemaError,
)

BASE = "https://elexon.test/bmrs/api/v1"
PATH = "/datasets/FUELHH/stream"


class Recorder:
    """Captures sleep calls and request attempts."""

    def __init__(self) -> None:
        self.delays: list[float] = []
        self.requests: list[httpx.Request] = []

    def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)

    def handler(self, response_factory):  # noqa: ANN001, ANN201
        def _handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return response_factory(len(self.requests))

        return _handle


def _client(handler, *, recorder: Recorder, max_attempts: int = 3) -> ElexonClient:
    return ElexonClient(
        BASE,
        transport=httpx.MockTransport(handler),
        sleep=recorder.sleep,
        jitter=lambda: 1.0,
        max_attempts=max_attempts,
        backoff_base_seconds=0.5,
        backoff_max_seconds=4.0,
    )


class TestSuccessPaths:
    def test_bare_array_payload(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(200, json=[{"a": 1}]))
        client = _client(handler, recorder=recorder)
        rows = client.get_rows(PATH, {"settlementDateFrom": "2026-01-01"})
        assert rows == [{"a": 1}]
        assert client.request_count == 1
        assert client.last_status == 200
        client.close()

    def test_wrapped_data_payload_is_accepted(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(200, json={"data": [{"b": 2}]}))
        client = _client(handler, recorder=recorder)
        assert client.get_rows(PATH, {}) == [{"b": 2}]
        client.close()

    def test_request_url_and_parameters(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(200, json=[]))
        client = _client(handler, recorder=recorder)
        client.get_rows(PATH, {"fuelType": "WIND"})
        request = recorder.requests[0]
        assert request.url.path == "/bmrs/api/v1/datasets/FUELHH/stream"
        assert request.url.params["fuelType"] == "WIND"
        client.close()


class TestRetries:
    def test_429_then_success_honours_retry_after(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(
            lambda n: httpx.Response(429, headers={"Retry-After": "2"})
            if n == 1
            else httpx.Response(200, json=[{"ok": True}])
        )
        client = _client(handler, recorder=recorder)
        assert client.get_rows(PATH, {}) == [{"ok": True}]
        assert recorder.delays == [2.0]
        assert client.request_count == 2
        client.close()

    def test_server_error_is_retried_with_backoff(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(
            lambda n: httpx.Response(503) if n < 3 else httpx.Response(200, json=[])
        )
        client = _client(handler, recorder=recorder)
        client.get_rows(PATH, {})
        assert len(recorder.requests) == 3
        assert recorder.delays == [0.5, 1.0]
        client.close()

    def test_parameter_error_is_not_retried(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(400, text="bad parameter"))
        client = _client(handler, recorder=recorder)
        with pytest.raises(ElexonParameterError) as excinfo:
            client.get_rows(PATH, {})
        assert excinfo.value.http_status == 400
        assert len(recorder.requests) == 1
        assert recorder.delays == []
        client.close()

    def test_exhausted_server_errors_raise_http_error(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(500, text="boom"))
        client = _client(handler, recorder=recorder, max_attempts=2)
        with pytest.raises(ElexonHTTPError) as excinfo:
            client.get_rows(PATH, {})
        assert excinfo.value.http_status == 500
        assert len(recorder.requests) == 2
        client.close()

    def test_transport_errors_are_retried_then_raised(self) -> None:
        recorder = Recorder()

        def handler(_request: httpx.Request) -> httpx.Response:
            recorder.requests.append(_request)
            raise httpx.ConnectError("connection refused")

        client = _client(handler, recorder=recorder, max_attempts=2)
        with pytest.raises(ElexonRequestError):
            client.get_rows(PATH, {})
        assert len(recorder.requests) == 2
        client.close()

    def test_404_is_not_retried(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(404))
        client = _client(handler, recorder=recorder)
        with pytest.raises(ElexonHTTPError):
            client.get_rows(PATH, {})
        assert len(recorder.requests) == 1
        client.close()


class TestPayloadValidation:
    def test_non_json_body_raises_schema_error(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(200, text="<html>nope</html>"))
        client = _client(handler, recorder=recorder)
        with pytest.raises(ElexonSchemaError):
            client.get_rows(PATH, {})
        client.close()

    def test_object_without_data_array_raises_schema_error(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(200, json={"unexpected": 1}))
        client = _client(handler, recorder=recorder)
        with pytest.raises(ElexonSchemaError):
            client.get_rows(PATH, {})
        client.close()

    def test_scalar_json_raises_schema_error(self) -> None:
        recorder = Recorder()
        handler = recorder.handler(lambda _n: httpx.Response(200, json=42))
        client = _client(handler, recorder=recorder)
        with pytest.raises(ElexonSchemaError):
            client.get_rows(PATH, {})
        client.close()


class TestBackoff:
    def test_exponential_growth_is_capped(self) -> None:
        assert backoff_delay(1, base_seconds=0.5, max_seconds=8, jitter=lambda: 1.0) == 0.5
        assert backoff_delay(2, base_seconds=0.5, max_seconds=8, jitter=lambda: 1.0) == 1.0
        assert backoff_delay(5, base_seconds=0.5, max_seconds=8, jitter=lambda: 1.0) == 8

    def test_retry_after_wins_but_is_capped(self) -> None:
        assert backoff_delay(1, base_seconds=0.5, max_seconds=8, retry_after=3) == 3.0
        assert backoff_delay(1, base_seconds=0.5, max_seconds=8, retry_after=60) == 8

    def test_jitter_is_applied(self) -> None:
        assert backoff_delay(1, base_seconds=2, max_seconds=8, jitter=lambda: 0.0) == 1.0
