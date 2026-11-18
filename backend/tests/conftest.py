"""Shared pytest fixtures.

The test suite runs against a **separate MySQL database** (``windpulse_test`` by
default, override with ``TEST_DATABASE_URL``). Every test starts from truncated
tables plus the seeded cutoff policies, so tests cannot see each other's rows and
nothing destructive ever touches the development database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:  # pragma: no cover - import-path guard
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "mysql+pymysql://windpulse:windpulse_pw@127.0.0.1:3307/windpulse_test?charset=utf8mb4",
)

# These must be set before application modules are imported so settings and the
# engine pick up the test database rather than the development one.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import build_engine, get_session  # noqa: E402
from app.main import create_app  # noqa: E402

get_settings.cache_clear()

TRUNCATE_ORDER = (
    "data_quality_issue",
    "forecast_selection",
    "actual_generation",
    "forecast_point",
    "forecast_vintage",
    "ingestion_watermark",
    "ingestion_run",
    "cutoff_policy",
)

POLICY_SEED_SQL = """
INSERT INTO cutoff_policy
  (code, name, local_time, timezone_id, offset_days, is_default, source_reference, notes)
VALUES
  ('EPEX_GB_DA_1H_0920',
   'EPEX SPOT GB Day-Ahead 60-minute auction gate closure (D-1 09:20 London)',
   '09:20:00', 'Europe/London', -1, 1, 'test fixture seed',
   'Default policy used by the test suite.'),
  ('N2EX_GB_DA_1H_0950',
   'Nord Pool N2EX GB day-ahead auction gate closure (D-1 09:50 London)',
   '09:50:00', 'Europe/London', -1, 0, 'test fixture seed', NULL),
  ('EPEX_GB_DA_30M_1530',
   'EPEX SPOT GB Day-Ahead 30-minute auction gate closure (D-1 15:30 London)',
   '15:30:00', 'Europe/London', -1, 0, 'test fixture seed', NULL)
"""


@pytest.fixture(scope="session")
def engine():  # noqa: ANN201
    """Session-scoped engine; migrates the test database once per run."""
    test_engine = build_engine(TEST_DATABASE_URL, pool_size=5)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def clean_db(engine):  # noqa: ANN001, ANN201
    """Truncate all data tables and re-seed policies before each DB test."""
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in TRUNCATE_ORDER:
            connection.execute(text(f"TRUNCATE TABLE {table}"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        connection.execute(text(POLICY_SEED_SQL))
    yield


@pytest.fixture
def session_factory(engine, clean_db):  # noqa: ANN001, ANN201
    """Session factory bound to the test database."""
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
def session(session_factory) -> Session:  # noqa: ANN001
    """A session for direct repository/service use."""
    with session_factory() as db_session:
        yield db_session


@pytest.fixture
def client(session_factory):  # noqa: ANN001, ANN201
    """A FastAPI test client wired to the test database."""
    app = create_app(get_settings())

    def _session_override():  # noqa: ANN202
        db_session = session_factory()
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    app.dependency_overrides[get_session] = _session_override
    with TestClient(app) as test_client:
        yield test_client
