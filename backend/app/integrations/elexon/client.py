"""HTTP client for the Elexon BMRS Insights API.

Behaviour implemented here (all of it exercised by tests):

* explicit connect/read timeouts;
* bounded retries with exponential backoff and jitter for transient failures
  (transport errors, 429, 5xx), honouring ``Retry-After``;
* no retry for 400 — that means our parameters are wrong, and repeating them
  only wastes the request budget;
* request accounting so ingestion runs can record how much upstream load they
  caused;
* strict payload shape handling: the stream endpoints return a bare JSON array;
  the non-stream endpoints wrap rows in ``{"data": [...]}``. Both are accepted,
  anything else raises ``ElexonSchemaError``.

The client is synchronous on purpose: ingestion is a batch job issuing sequential
chunked requests, and synchronous code keeps the retry/backoff loop simple and
deterministic under test.
"""

from __future__ import annotations

import random
from types import TracebackType
from typing import Any, Callable

import httpx

from app.core.logging import get_logger
from app.integrations.elexon.errors import (
    ElexonHTTPError,
    ElexonParameterError,
    ElexonRequestError,
    ElexonSchemaError,
)

logger = get_logger(__name__)

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def backoff_delay(
    attempt: int,
    *,
    base_seconds: float,
    max_seconds: float,
    retry_after: float | None = None,
    jitter: Callable[[], float] | None = None,
) -> float:
    """Delay before the next attempt, in seconds.

    ``attempt`` is 1-based (the attempt that just failed). An explicit
    ``Retry-After`` wins, capped at ``max_seconds``; otherwise exponential
    backoff with full jitter.
    """
    if retry_after is not None:
        return max(0.0, min(retry_after, max_seconds))
    raw = base_seconds * (2 ** (attempt - 1))
    capped = min(raw, max_seconds)
    randomiser = jitter or random.random
    return capped * (0.5 + 0.5 * randomiser())


def _retry_after_seconds(response: httpx.Response) -> float | None:
    header = response.headers.get("Retry-After")
    if not header:
        return None
    try:
        return float(header)
    except ValueError:
        return None


class ElexonClient:
    """Thin, well-behaved wrapper around the Elexon Insights API."""

    def __init__(
        self,
        base_url: str,
        *,
        connect_timeout_seconds: float = 10.0,
        read_timeout_seconds: float = 30.0,
        max_attempts: int = 4,
        backoff_base_seconds: float = 0.5,
        backoff_max_seconds: float = 8.0,
        user_agent: str = "WindPulseUK/0.2",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] | None = None,
        jitter: Callable[[], float] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_attempts = max(1, max_attempts)
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_max_seconds = backoff_max_seconds
        self._sleep = sleep or (lambda seconds: __import__("time").sleep(seconds))
        self._jitter = jitter
        self.request_count = 0
        # Successful response bodies, kept so an ingestion run can record a
        # checksum of exactly what upstream served. Bounded by the run's window
        # (a two-month backfill is a few megabytes) and discarded when the client
        # is closed, so a long-lived worker is not needed for this to be safe.
        self.response_bodies: list[str] = []
        self._current_status: int | None = None
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=connect_timeout_seconds,
                read=read_timeout_seconds,
                write=read_timeout_seconds,
                pool=connect_timeout_seconds,
            ),
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            transport=transport,
            follow_redirects=False,
        )

    # ── context management ────────────────────────────────────────────────
    def __enter__(self) -> "ElexonClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying connection pool."""
        self._client.close()

    # ── requests ──────────────────────────────────────────────────────────
    def get_rows(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """GET ``path`` and return the payload's row list.

        Raises ``ElexonParameterError`` for 400, ``ElexonHTTPError`` for other
        non-retryable statuses, ``ElexonRequestError`` when transport errors
        persist, and ``ElexonSchemaError`` for an unparseable payload.
        """
        last_transport_error: Exception | None = None
        last_response: httpx.Response | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._client.get(path, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_transport_error = exc
                logger.warning(
                    "elexon_transport_error",
                    extra={"path": path, "attempt": attempt, "error": repr(exc)},
                )
                if attempt >= self.max_attempts:
                    break
                self._sleep(
                    backoff_delay(
                        attempt,
                        base_seconds=self.backoff_base_seconds,
                        max_seconds=self.backoff_max_seconds,
                        jitter=self._jitter,
                    )
                )
                continue

            self.request_count += 1
            self._current_status = response.status_code
            last_response = response

            if response.status_code == 200:
                self.response_bodies.append(response.text)
                return self._parse_rows(response, path)

            if response.status_code == 400:
                raise ElexonParameterError(
                    f"Elexon rejected the query parameters for {path}",
                    http_status=400,
                    body=response.text[:1000],
                )

            if response.status_code in RETRYABLE_STATUSES and attempt < self.max_attempts:
                delay = backoff_delay(
                    attempt,
                    base_seconds=self.backoff_base_seconds,
                    max_seconds=self.backoff_max_seconds,
                    retry_after=_retry_after_seconds(response),
                    jitter=self._jitter,
                )
                logger.warning(
                    "elexon_retryable_status",
                    extra={
                        "path": path,
                        "status": response.status_code,
                        "attempt": attempt,
                        "delay_seconds": round(delay, 3),
                    },
                )
                self._sleep(delay)
                continue

            raise ElexonHTTPError(
                f"Elexon returned HTTP {response.status_code} for {path}",
                http_status=response.status_code,
                body=response.text[:1000],
            )

        if last_transport_error is not None:
            raise ElexonRequestError(
                f"Elexon request to {path} failed after {self.max_attempts} attempts: "
                f"{last_transport_error!r}"
            )
        status = last_response.status_code if last_response is not None else None
        raise ElexonHTTPError(
            f"Elexon request to {path} failed after {self.max_attempts} attempts",
            http_status=status,
            body=last_response.text[:1000] if last_response is not None else None,
        )

    @property
    def last_status(self) -> int | None:
        """HTTP status of the most recent response, for run bookkeeping."""
        return self._current_status

    # ── parsing ───────────────────────────────────────────────────────────
    @staticmethod
    def _parse_rows(response: httpx.Response, path: str) -> list[dict[str, Any]]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ElexonSchemaError(
                f"Elexon response for {path} was not valid JSON: {exc}",
                http_status=response.status_code,
                body=response.text[:1000],
            ) from exc

        if isinstance(payload, dict):
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise ElexonSchemaError(
                    f"Elexon response for {path} is an object without a 'data' array",
                    http_status=response.status_code,
                    body=response.text[:1000],
                )
            return rows

        if isinstance(payload, list):
            return payload

        raise ElexonSchemaError(
            f"Elexon response for {path} has unexpected JSON type {type(payload).__name__}",
            http_status=response.status_code,
        )
