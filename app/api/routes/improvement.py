"""Improvement and controlled reconstruction API route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.config import Settings, get_settings
from app.schemas.improvement import ImproveRequest, ImproveResponse
from app.services.improver import improve_text

router = APIRouter(tags=["Improvement"])


@router.post(
    "/improve",
    response_model=ImproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate reviewable text improvement suggestions",
    description=(
        "Analyzes text patterns and provides reviewable opportunities to reduce "
        "unnecessary repetition, vary monotonous sentence structures, and remove "
        "redundant phrasing. Every suggestion includes factual and certainty "
        "preservation verification. The system never silently alters text."
    ),
)
@router.post(
    "/reconstruct",
    response_model=ImproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Controlled reconstruction (alias for /improve)",
    description=(
        "Controlled text reconstruction endpoint providing reviewable suggestions "
        "for user consideration. Alias for /improve."
    ),
    include_in_schema=True,
)
async def improve_passage(
    request: ImproveRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImproveResponse:
    """Generate reviewable text improvement recommendations for submitted text."""
    return improve_text(
        text=request.text,
        settings=settings,
        include_draft_preview=request.include_draft_preview,
    )
