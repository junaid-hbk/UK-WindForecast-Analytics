"""Metadata exposed to clients so the UI never hard-codes policy or method details."""

from __future__ import annotations

from datetime import time
from typing import Any

from pydantic import BaseModel


class CutoffPolicyOut(BaseModel):
    """A configurable day-ahead decision cutoff."""

    code: str
    name: str
    local_time: time
    timezone_id: str
    offset_days: int
    is_default: bool
    source_reference: str | None = None
    notes: str | None = None


class MetaConfigOut(BaseModel):
    """Platform configuration and methodology flags."""

    app_version: str
    environment: str
    timezone_display: str
    timezone_storage: str
    cutoff_policies: list[CutoffPolicyOut]
    default_cutoff_policy: str
    windfor_sp_mapping: str
    forecast_resolution_minutes: int
    settlement_period_minutes: int
    metric_definitions: dict[str, str]
    data_sources: dict[str, Any]
    disclaimers: dict[str, str]
