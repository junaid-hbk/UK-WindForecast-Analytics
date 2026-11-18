"""Shared response envelopes and pagination metadata."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """Every successful response is ``{data, meta}``."""

    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


class PaginationMeta(BaseModel):
    """Pagination information for list responses."""

    limit: int
    offset: int
    total: int
    returned: int


class ErrorDetail(BaseModel):
    """Machine-readable error payload."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """Error response body."""

    error: ErrorDetail


class HealthOut(BaseModel):
    """Liveness payload."""

    status: str
    app: str
    version: str
    environment: str


class ReadinessOut(BaseModel):
    """Readiness payload including database and schema state."""

    status: str
    database: str
    alembic_revision: str | None = None
    detail: str | None = None
