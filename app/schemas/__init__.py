"""Schemas package for Untangle."""

from app.schemas.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    Finding,
    RepeatedItem,
    RepeatedPhrase,
    TextSpan,
    TextStatistics,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ReadinessResponse,
)
from app.schemas.improvement import (
    ImprovementSuggestion,
    ImproveRequest,
    ImproveResponse,
    PreservationCheck,
)

__all__ = [
    "AnalyzeRequest",
    "AnalyzeResponse",
    "ErrorDetail",
    "ErrorResponse",
    "Finding",
    "HealthResponse",
    "ImproveRequest",
    "ImproveResponse",
    "ImprovementSuggestion",
    "PreservationCheck",
    "ReadinessResponse",
    "RepeatedItem",
    "RepeatedPhrase",
    "TextSpan",
    "TextStatistics",
]
