"""Elexon-specific failures.

These are deliberately distinct from generic HTTP errors so callers can tell a
transient outage (retry later, keep existing data) from a wrong query (a bug in
our parameters) or a payload we cannot parse (upstream schema change).
"""

from __future__ import annotations


class ElexonError(Exception):
    """Base class for all Elexon integration failures."""

    code = "ELEXON_ERROR"

    def __init__(self, message: str, *, http_status: int | None = None, body: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.body = body


class ElexonRequestError(ElexonError):
    """Transport-level failure: timeout, DNS, connection reset after all retries."""

    code = "ELEXON_TRANSPORT_ERROR"


class ElexonHTTPError(ElexonError):
    """An unexpected HTTP status after retries were exhausted."""

    code = "ELEXON_HTTP_ERROR"


class ElexonParameterError(ElexonError):
    """HTTP 400 — our query parameters are wrong. Never retried."""

    code = "ELEXON_PARAMETER_ERROR"


class ElexonSchemaError(ElexonError):
    """The response body is not JSON or does not match the documented row shape."""

    code = "ELEXON_SCHEMA_ERROR"
