"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.models.actual import ActualGeneration
from app.models.base import Base
from app.models.cutoff import CutoffPolicy
from app.models.forecast import ForecastPoint, ForecastVintage
from app.models.ingestion import IngestionRun, IngestionWatermark
from app.models.quality import DataQualityIssue
from app.models.selection import ForecastSelection

__all__ = [
    "ActualGeneration",
    "Base",
    "CutoffPolicy",
    "DataQualityIssue",
    "ForecastPoint",
    "ForecastSelection",
    "ForecastVintage",
    "IngestionRun",
    "IngestionWatermark",
]
