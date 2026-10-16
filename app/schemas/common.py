"""Common Pydantic schemas for Untangle."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Schema for health check endpoint response."""

    status: str = Field(
        default="ok",
        description="Health status indicator.",
        examples=["ok"],
    )
    application: str = Field(
        description="Application name.",
        examples=["Untangle"],
    )
    version: str = Field(
        description="Application semantic version.",
        examples=["0.1.0"],
    )

    model_config = ConfigDict(extra="forbid")


class ReadinessResponse(BaseModel):
    """Schema for readiness check endpoint response."""

    status: str = Field(
        default="ready",
        description="Readiness status indicator.",
        examples=["ready"],
    )
    application: str = Field(
        description="Application name.",
        examples=["Untangle"],
    )
    version: str = Field(
        description="Application semantic version.",
        examples=["0.1.0"],
    )

    model_config = ConfigDict(extra="forbid")


class ErrorDetail(BaseModel):
    """Schema representing error details."""

    code: str = Field(
        description="Machine-readable error code.",
        examples=["NOT_FOUND"],
    )
    message: str = Field(
        description="Human-readable description of the error.",
        examples=["The requested resource was not found."],
    )
    details: Any | None = Field(
        default=None,
        description="Optional additional context or validation breakdown.",
    )

    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    """Standard API error response schema."""

    status: str = Field(
        default="error",
        description="Response status indicating error.",
        examples=["error"],
    )
    error: ErrorDetail = Field(
        description="Structured error information.",
    )

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> "ErrorResponse":
        """Convenience factory method to construct an ErrorResponse."""
        return cls(error=ErrorDetail(code=code, message=message, details=details))
