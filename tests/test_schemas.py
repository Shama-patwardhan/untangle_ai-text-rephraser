"""Tests for Pydantic schemas and application configuration."""

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.core.exceptions import (
    AppValidationError,
    ConfigurationError,
    ResourceNotFoundError,
    UntangleError,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ReadinessResponse,
)

# --- HealthResponse Tests ---


def test_health_response_valid_defaults() -> None:
    """Test HealthResponse with default status and required fields."""
    response = HealthResponse(application="Untangle", version="0.1.0")
    assert response.status == "ok"
    assert response.application == "Untangle"
    assert response.version == "0.1.0"


def test_health_response_valid_explicit() -> None:
    """Test HealthResponse with explicit fields."""
    response = HealthResponse(
        status="healthy", application="CustomApp", version="1.0.0"
    )
    assert response.status == "healthy"
    assert response.application == "CustomApp"
    assert response.version == "1.0.0"


def test_health_response_missing_fields() -> None:
    """Test HealthResponse validation fails when required fields are missing."""
    with pytest.raises(ValidationError):
        HealthResponse.model_validate({"status": "ok"})


def test_health_response_forbid_extra_fields() -> None:
    """Test HealthResponse rejects unexpected extra fields."""
    with pytest.raises(ValidationError):
        HealthResponse.model_validate(
            {"application": "Untangle", "version": "0.1.0", "unexpected": "value"}
        )


# --- ReadinessResponse Tests ---


def test_readiness_response_valid_defaults() -> None:
    """Test ReadinessResponse with default status."""
    response = ReadinessResponse(application="Untangle", version="0.1.0")
    assert response.status == "ready"
    assert response.application == "Untangle"
    assert response.version == "0.1.0"


def test_readiness_response_missing_fields() -> None:
    """Test ReadinessResponse fails when required fields are missing."""
    with pytest.raises(ValidationError):
        ReadinessResponse.model_validate({"status": "ready"})


def test_readiness_response_forbid_extra_fields() -> None:
    """Test ReadinessResponse rejects unexpected extra fields."""
    with pytest.raises(ValidationError):
        ReadinessResponse.model_validate(
            {"application": "Untangle", "version": "0.1.0", "extra_prop": 123}
        )


# --- ErrorDetail and ErrorResponse Tests ---


def test_error_detail_valid() -> None:
    """Test ErrorDetail schema with valid inputs."""
    detail = ErrorDetail(code="NOT_FOUND", message="Item not found", details={"id": 42})
    assert detail.code == "NOT_FOUND"
    assert detail.message == "Item not found"
    assert detail.details == {"id": 42}


def test_error_detail_missing_fields() -> None:
    """Test ErrorDetail validation fails when required fields are missing."""
    with pytest.raises(ValidationError):
        ErrorDetail.model_validate({"code": "ERR"})


def test_error_response_valid() -> None:
    """Test ErrorResponse schema with valid inputs."""
    detail = ErrorDetail(code="BAD_REQUEST", message="Invalid payload")
    err = ErrorResponse(status="error", error=detail)
    assert err.status == "error"
    assert err.error.code == "BAD_REQUEST"
    assert err.error.message == "Invalid payload"


def test_error_response_create_helper() -> None:
    """Test ErrorResponse.create factory method."""
    err = ErrorResponse.create(
        code="UNAUTHORIZED",
        message="Missing credentials",
        details=["auth header required"],
    )
    assert err.status == "error"
    assert err.error.code == "UNAUTHORIZED"
    assert err.error.message == "Missing credentials"
    assert err.error.details == ["auth header required"]


def test_error_response_forbid_extra() -> None:
    """Test ErrorResponse rejects unknown extra fields."""
    with pytest.raises(ValidationError):
        ErrorResponse.model_validate(
            {
                "status": "error",
                "error": {"code": "ERR", "message": "msg"},
                "extra": "value",
            }
        )


# --- Configuration (Settings) Tests ---


def test_settings_defaults() -> None:
    """Test Settings safe default values."""
    settings = Settings()
    assert settings.app_name == "Untangle"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"
    assert settings.api_prefix == "/api/v1"
    assert settings.debug is False


def test_settings_custom_values() -> None:
    """Test Settings with custom values."""
    settings = Settings(
        app_name="Untangle-Test",
        app_version="2.0.0",
        environment="test",
        api_prefix="/custom/v2",
        debug=True,
    )
    assert settings.app_name == "Untangle-Test"
    assert settings.app_version == "2.0.0"
    assert settings.environment == "test"
    assert settings.api_prefix == "/custom/v2"
    assert settings.debug is True


def test_settings_api_prefix_normalization() -> None:
    """Test Settings normalizes api_prefix slashes."""
    s1 = Settings(api_prefix="v1")
    assert s1.api_prefix == "/v1"

    s2 = Settings(api_prefix="/api/v1/")
    assert s2.api_prefix == "/api/v1"

    s3 = Settings(api_prefix="  api/test/  ")
    assert s3.api_prefix == "/api/test"


def test_settings_invalid_environment() -> None:
    """Test Settings rejects unapproved environment values."""
    with pytest.raises(ValidationError):
        Settings(environment="non_existent_env")  # type: ignore[arg-type]


# --- Core Exceptions Tests ---


def test_core_exceptions_hierarchy() -> None:
    """Test core domain exception classes and properties."""
    base_err = UntangleError("Base error", code="BASE_ERR", status_code=500)
    assert base_err.message == "Base error"
    assert base_err.code == "BASE_ERR"
    assert base_err.status_code == 500

    cfg_err = ConfigurationError("Config failed")
    assert isinstance(cfg_err, UntangleError)
    assert cfg_err.code == "CONFIGURATION_ERROR"
    assert cfg_err.status_code == 500

    nf_err = ResourceNotFoundError("Doc missing")
    assert isinstance(nf_err, UntangleError)
    assert nf_err.code == "RESOURCE_NOT_FOUND"
    assert nf_err.status_code == 404

    val_err = AppValidationError("Invalid format")
    assert isinstance(val_err, UntangleError)
    assert val_err.code == "VALIDATION_ERROR"
    assert val_err.status_code == 422
