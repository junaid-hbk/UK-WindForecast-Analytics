"""Repositories package."""

from app.repositories.actual_generation_repository import (
    ActualGenerationRepository,
    ActualPoint,
    ActualUpsertResult,
)
from app.repositories.base import BaseRepository
from app.repositories.cutoff_policy_repository import CutoffPolicyRepository
from app.repositories.data_quality_repository import DataQualityRepository, QualityIssue
from app.repositories.data_status_repository import CoverageDay, DataStatusRepository
from app.repositories.forecast_selection_repository import (
    AnalysisInterval,
    ForecastSelectionRepository,
    SelectionRow,
)
from app.repositories.forecast_vintage_repository import (
    ForecastVintageRepository,
    SelectionInputs,
    VintageUpsertResult,
)
from app.repositories.ingestion_run_repository import IngestionRunRepository, RunCounts

__all__ = [
    "ActualGenerationRepository",
    "ActualPoint",
    "ActualUpsertResult",
    "AnalysisInterval",
    "BaseRepository",
    "CoverageDay",
    "CutoffPolicyRepository",
    "DataQualityRepository",
    "DataStatusRepository",
    "ForecastSelectionRepository",
    "ForecastVintageRepository",
    "IngestionRunRepository",
    "QualityIssue",
    "RunCounts",
    "SelectionInputs",
    "SelectionRow",
    "VintageUpsertResult",
]
