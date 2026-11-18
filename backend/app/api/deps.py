"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_session

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


class AuthenticationError(AppError):
    """Missing or wrong administrative token."""

    code = "UNAUTHORIZED"
    status_code = 401


class AdminDisabledError(AppError):
    """Administrative routes exist but no token is configured."""

    code = "ADMIN_DISABLED"
    status_code = 503


def require_admin(
    settings: SettingsDep,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    """Guard destructive/ingestion routes with a configured shared token.

    When ``ADMIN_TOKEN`` is unset the endpoints are disabled outright rather than
    left open, so a deployment cannot accidentally expose ingestion.
    """
    if not settings.admin_enabled:
        raise AdminDisabledError(
            "Administrative endpoints are disabled: set ADMIN_TOKEN to enable them."
        )
    if x_admin_token is None or x_admin_token != settings.admin_token:
        raise AuthenticationError("A valid X-Admin-Token header is required.")
