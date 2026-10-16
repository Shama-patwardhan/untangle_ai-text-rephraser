"""Application core exceptions and error handling foundation."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


class UntangleError(Exception):
    """Base exception for all Untangle domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "UNTANGLE_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class ConfigurationError(UntangleError):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ResourceNotFoundError(UntangleError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Any | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class AppValidationError(UntangleError):
    """Raised when domain validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Any | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with the FastAPI application."""

    @app.exception_handler(UntangleError)
    async def untangle_error_handler(
        _request: Request,
        exc: UntangleError,
    ) -> JSONResponse:
        """Handle domain-specific Untangle errors."""
        error_body = ErrorResponse.create(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body.model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        """Handle standard HTTP exceptions."""
        detail_msg = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        error_body = ErrorResponse.create(
            code=f"HTTP_{exc.status_code}",
            message=detail_msg,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle request schema validation errors without exposing sensitive data."""
        sanitized_errors = [
            {
                "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", "Invalid value"),
            }
            for err in exc.errors()
        ]
        error_body = ErrorResponse.create(
            code="REQUEST_VALIDATION_ERROR",
            message="Request input validation failed.",
            details=sanitized_errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unhandled server exceptions safely without leaking internal traces."""
        logger.error("Unhandled server exception: %s", exc, exc_info=True)
        error_body = ErrorResponse.create(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body.model_dump(),
        )
