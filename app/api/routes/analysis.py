"""Analysis API route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.config import Settings, get_settings
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer import analyze_text

router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze text patterns",
    description=(
        "Analyzes an input text passage for deterministic structural metrics "
        "and observable stylistic patterns. Stylistic patterns describe "
        "observable characteristics and do not claim to determine AI authorship."
    ),
)
async def analyze_passage(
    request: AnalyzeRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnalyzeResponse:
    """Execute writing pattern analysis on the submitted text."""
    return analyze_text(text=request.text, settings=settings)
