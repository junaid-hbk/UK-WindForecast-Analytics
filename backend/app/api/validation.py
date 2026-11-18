"""Request-level validation helpers shared by routes."""

from __future__ import annotations

from datetime import date

from app.core.errors import (
    InvalidRequestError,
    RangeTooLargeError,
    UnprocessableRequestError,
)


def ensure_date_range(date_from: date, date_to: date, max_days: int) -> None:
    """Reject inverted or oversized date ranges before any query runs."""
    if date_to < date_from:
        raise InvalidRequestError(
            "'to' must not precede 'from'.", details={"from": str(date_from), "to": str(date_to)}
        )
    span = (date_to - date_from).days + 1
    if span > max_days:
        raise RangeTooLargeError(
            f"Requested range of {span} days exceeds the {max_days}-day maximum.",
            details={"from": str(date_from), "to": str(date_to), "max_days": max_days},
        )


def ensure_pagination(limit: int, offset: int, max_limit: int) -> None:
    """Reject out-of-bounds pagination parameters.

    These are schema-level bounds, so they answer 422 (like a Pydantic
    constraint) rather than 400, which is reserved for semantically impossible
    requests such as an inverted date range.
    """
    if limit < 1 or limit > max_limit:
        raise UnprocessableRequestError(
            f"limit must be between 1 and {max_limit}.",
            details={"limit": limit, "min": 1, "max": max_limit},
        )
    if offset < 0:
        raise UnprocessableRequestError("offset must be zero or positive.")
