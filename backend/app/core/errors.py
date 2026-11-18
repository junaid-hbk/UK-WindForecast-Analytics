"""Domain-level exceptions shared across layers.

These are transport-agnostic. The API layer maps them to HTTP problem details so
services and repositories never import FastAPI.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, user-facing application errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    """A requested entity does not exist."""

    code = "NOT_FOUND"
    status_code = 404


class InvalidRequestError(AppError):
    """A request is syntactically valid but semantically impossible."""

    code = "INVALID_REQUEST"
    status_code = 400


class UnprocessableRequestError(AppError):
    """A parameter is well-formed but outside its allowed bounds (HTTP 422)."""

    code = "VALIDATION_ERROR"
    status_code = 422


class RangeTooLargeError(InvalidRequestError):
    """A requested analysis window exceeds the configured maximum."""

    code = "RANGE_TOO_LARGE"


class DataUnavailableError(AppError):
    """The requested analysis needs data that has not been ingested."""

    code = "DATA_UNAVAILABLE"
    status_code = 409


class UpstreamServiceError(AppError):
    """An external data provider failed."""

    code = "UPSTREAM_ERROR"
    status_code = 502
