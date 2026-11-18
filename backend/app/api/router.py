"""Aggregate API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    actuals,
    admin,
    analysis,
    data_status,
    forecasts,
    health,
    meta,
    procurement,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(meta.router)
api_router.include_router(actuals.router)
api_router.include_router(forecasts.router)
api_router.include_router(analysis.router)
api_router.include_router(procurement.router)
api_router.include_router(data_status.router)
api_router.include_router(admin.router)
