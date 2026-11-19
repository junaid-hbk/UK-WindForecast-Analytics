
"""Engine and session management for MySQL (SQLAlchemy 2 + PyMySQL)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


CA_CERT_PATH = "/etc/secrets/ca.pem"


def _pin_session_timezone(
    dbapi_connection: object,
    _connection_record: object,
) -> None:
    """Force every new DB-API connection into UTC."""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    try:
        cursor.execute("SET time_zone = '+00:00'")
    finally:
        cursor.close()


def build_engine(
    url: str,
    *,
    pool_size: int = 5,
    recycle: int = 1800,
    echo: bool = False,
) -> Engine:
    """Create a MySQL engine with verified Aiven SSL."""

    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=recycle,
        pool_size=pool_size,
        max_overflow=pool_size,
        echo=echo,
        future=True,
        connect_args={
            "ssl_ca": CA_CERT_PATH,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
            "connect_timeout": 15,
        },
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
    """FastAPI dependency: one session per request."""
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
    """Context manager with an explicit commit/rollback boundary."""
    session = get_session_factory()()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
