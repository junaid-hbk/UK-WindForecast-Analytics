"""Exception handlers: one error envelope for the whole API."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.errors import AppError
from app.core.logging import get_logger
from app.integrations.elexon.errors import ElexonError

logger = get_logger(__name__)


def _error(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": jsonable_encoder(details or {}),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers for domain, upstream, validation and database errors."""

    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            # The extra key must not be "message": Python's logging raises
            # ``KeyError: Attempt to overwrite 'message' in LogRecord``, which
            # would replace the intended status with a generic 500.
            logger.error("app_error", extra={"code": exc.code, "error_message": exc.message})
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(ElexonError)
    async def _elexon_error(_request: Request, exc: ElexonError) -> JSONResponse:
        logger.error(
            "upstream_error",
            extra={
                "code": exc.code,
                "error_message": exc.message,
                "http_status": exc.http_status,
            },
        )
        return _error(
            502,
            exc.code,
            f"Elexon request failed: {exc.message}",
            {"http_status": exc.http_status},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(
            422,
            "VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": exc.errors()},
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("integrity_error", extra={"error": str(exc.orig)})
        return _error(409, "CONFLICT", "The request conflicts with the stored data.")

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("database_error", extra={"error": type(exc).__name__})
        return _error(503, "DATABASE_UNAVAILABLE", "The database is not available.")

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error")
        return _error(500, "INTERNAL_ERROR", "An unexpected error occurred.")
