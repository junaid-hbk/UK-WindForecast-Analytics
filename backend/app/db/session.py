"""Engine and session management for MySQL (SQLAlchemy 2 + PyMySQL).

Conventions enforced here:

* the connection time zone is pinned to UTC, so ``CURRENT_TIMESTAMP`` defaults
  and ``UTC_TIMESTAMP()`` produce the same values regardless of the client host;
* ``pool_pre_ping`` avoids serving stale connections after a managed-MySQL
  failover or a container restart;
* sessions are created per request/CLI command and closed deterministically.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _pin_session_timezone(dbapi_connection: object, _connection_record: object) -> None:
    """Force every new DB-API connection into UTC."""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    try:
        cursor.execute("SET time_zone = '+00:00'")
    finally:
        cursor.close()


def build_engine(url: str, *, pool_size: int = 5, recycle: int = 1800, echo: bool = False) -> Engine:
    """Create a MySQL engine with project-standard settings."""
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=recycle,
        pool_size=pool_size,
        max_overflow=pool_size,
        echo=echo,
        future=True,
    )
    event.listen(engine, "connect", _pin_session_timezone)
    return engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Process-wide engine built from settings."""
    settings = get_settings()
    return build_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        recycle=settings.database_pool_recycle_seconds,
        echo=settings.database_echo,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Process-wide session factory."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed on success.

    The route/service layer flushes; this dependency owns the commit boundary, so
    a failure anywhere in the request rolls the whole unit of work back.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager with an explicit commit/rollback boundary (CLI, services)."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
