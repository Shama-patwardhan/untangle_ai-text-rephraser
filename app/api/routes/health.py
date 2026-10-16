"""Health and readiness check route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.config import Settings, get_settings
from app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns the operational status and metadata of the application.",
)
async def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Return application health status."""
    return HealthResponse(
        status="ok",
        application=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Returns whether the application has initialized successfully.",
)
async def get_readiness(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    """Return application readiness status."""
    return ReadinessResponse(
        status="ready",
        application=settings.app_name,
        version=settings.app_version,
    )
