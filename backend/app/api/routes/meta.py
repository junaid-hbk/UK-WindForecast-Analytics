"""Metadata endpoint: policies, method flags and disclaimers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep, SettingsDep
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.schemas.common import Envelope
from app.schemas.meta import CutoffPolicyOut, MetaConfigOut
from app.services.procurement_service import DISCLAIMER

router = APIRouter(tags=["meta"])

METRIC_DEFINITIONS = {
    "error": "e = forecast_mw - actual_mw. Positive means the forecast was too high (over-forecast).",
    "mae": "Mean absolute error in MW over evaluated intervals.",
    "rmse": "Square root of the mean squared error in MW; penalises large misses.",
    "wape": "100 * sum(|e|) / sum(|actual|). Undefined when sum(|actual|) is zero.",
    "bias": "Mean signed error in MW; positive means systematic over-forecast.",
    "bias_pct": "100 * sum(e) / sum(actual).",
    "coverage": "Evaluated intervals / expected intervals, expressed as a percentage.",
    "n": "Number of intervals with both a forecast and an actual. Reported with every metric.",
}

DATA_SOURCES = {
    "actual_generation": {
        "dataset": "FUELHH",
        "provider": "Elexon BMRS Insights API",
        "endpoint": "/datasets/FUELHH/stream",
        "filter": "fuelType=WIND",
        "fields": ["startTime", "generation"],
        "resolution_minutes": 30,
    },
    "forecast_generation": {
        "dataset": "WINDFOR",
        "provider": "Elexon BMRS Insights API",
        "endpoint": "/datasets/WINDFOR/stream",
        "fields": ["startTime", "publishTime", "generation"],
        "resolution_minutes": 60,
        "note": "Published hourly; vintages are preserved individually.",
    },
}


@router.get(
    "/meta/config",
    response_model=Envelope[MetaConfigOut],
    summary="Cutoff policies, method flags and disclaimers",
)
def get_meta(session: SessionDep, settings: SettingsDep) -> Envelope[MetaConfigOut]:
    """Describe the platform's configuration so clients hard-code nothing."""
    repo = CutoffPolicyRepository(session)
    policies = repo.list_all()
    default = repo.get_default()
    payload = MetaConfigOut(
        app_version=settings.app_version,
        environment=settings.environment,
        timezone_display="Europe/London",
        timezone_storage="UTC",
        cutoff_policies=[
            CutoffPolicyOut(
                code=policy.code,
                name=policy.name,
                local_time=policy.local_time,
                timezone_id=policy.timezone_id,
                offset_days=policy.offset_days,
                is_default=policy.is_default,
                source_reference=policy.source_reference,
                notes=policy.notes,
            )
            for policy in policies
        ],
        default_cutoff_policy=default.code,
        windfor_sp_mapping=settings.windfor_sp_mapping,
        forecast_resolution_minutes=60,
        settlement_period_minutes=30,
        metric_definitions=METRIC_DEFINITIONS,
        data_sources=DATA_SOURCES,
        disclaimers={
            "procurement": DISCLAIMER,
            "forecast_resolution": (
                "WINDFOR is published hourly while settlement periods are 30 minutes. "
                "Half-hourly values are a documented mapping of the hourly forecast, not "
                "additional information."
            ),
            "comparability": (
                "FUELHH WIND outturn and WINDFOR forecast are the only permitted pair. "
                "Differences in the underlying wind fleet definition are not modelled."
            ),
        },
    )
    return Envelope(data=payload, meta={"policies": len(policies)})
