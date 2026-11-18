"""Environment-driven configuration.

All values are read from environment variables (or a local ``.env`` file). No
credential is ever hard-coded: ``DATABASE_URL`` has no default password-bearing
value in production use, and ``.env.example`` documents the required variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings resolved from the environment."""

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── application ──────────────────────────────────────────────────────
    app_name: str = "WindPulse UK API"
    app_version: str = "0.2.0"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # ── database ─────────────────────────────────────────────────────────
    database_url: str = Field(
        default="mysql+pymysql://windpulse:windpulse_pw@127.0.0.1:3307/windpulse?charset=utf8mb4",
        description="SQLAlchemy URL. Override in .env; never commit real credentials.",
    )
    database_pool_size: int = 5
    database_pool_recycle_seconds: int = 1800
    database_echo: bool = False

    # ── Elexon BMRS ──────────────────────────────────────────────────────
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_connect_timeout_seconds: float = 10.0
    elexon_read_timeout_seconds: float = 30.0
    elexon_max_attempts: int = 4
    elexon_backoff_base_seconds: float = 0.5
    elexon_backoff_max_seconds: float = 8.0
    elexon_actual_chunk_days: int = 7
    elexon_forecast_chunk_days: int = 1
    elexon_user_agent: str = "WindPulseUK/0.2 (UK wind forecast accuracy research)"

    # ── analysis ─────────────────────────────────────────────────────────
    default_cutoff_policy_code: str = "EPEX_GB_DA_1H_0920"
    windfor_sp_mapping: Literal["step", "linear"] = "step"
    max_query_days: int = 180

    # ── HTTP surface ─────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_token: str | None = None
    page_size_default: int = 500
    page_size_max: int = 5000

    @field_validator("elexon_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list, from the comma-separated setting."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def admin_enabled(self) -> bool:
        """Administrative ingestion endpoints require an explicitly configured token."""
        return bool(self.admin_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
