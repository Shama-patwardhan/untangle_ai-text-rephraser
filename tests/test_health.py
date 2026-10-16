"""Tests for FastAPI application initialization and health endpoints."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.exceptions import UntangleError
from app.main import app, create_app
from app.schemas.common import HealthResponse, ReadinessResponse


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a TestClient for the default application."""
    return TestClient(app)


def test_app_initialization() -> None:
    """Test that the application initializes successfully with expected metadata."""
    assert isinstance(app, FastAPI)
    assert app.title == "Untangle"
    assert app.version == "0.1.0"
    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"


def test_health_endpoint_success(client: TestClient) -> None:
    """Test GET /api/v1/health returns 200 and matches HealthResponse schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "ok"
    assert data["application"] == "Untangle"
    assert data["version"] == "0.1.0"

    # Validate against Pydantic schema
    validated = HealthResponse.model_validate(data)
    assert validated.status == "ok"
    assert validated.application == "Untangle"
    assert validated.version == "0.1.0"


def test_readiness_endpoint_success(client: TestClient) -> None:
    """Test GET /api/v1/health/ready returns 200 and matches schema."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "ready"
    assert data["application"] == "Untangle"
    assert data["version"] == "0.1.0"

    # Validate against Pydantic schema
    validated = ReadinessResponse.model_validate(data)
    assert validated.status == "ready"
    assert validated.application == "Untangle"
    assert validated.version == "0.1.0"


def test_configurable_api_prefix() -> None:
    """Test that the application respects a custom API prefix."""
    custom_prefix = "/api/v2"
    custom_settings = Settings(
        app_name="UntangleCustom",
        app_version="0.2.0",
        api_prefix=custom_prefix,
    )
    custom_app = create_app(settings=custom_settings)
    custom_client = TestClient(custom_app)

    # Health endpoint under custom prefix should succeed
    response = custom_client.get(f"{custom_prefix}/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["application"] == "UntangleCustom"
    assert data["version"] == "0.2.0"

    # Readiness endpoint under custom prefix should succeed
    ready_response = custom_client.get(f"{custom_prefix}/health/ready")
    assert ready_response.status_code == status.HTTP_200_OK
    ready_data = ready_response.json()
    assert ready_data["status"] == "ready"

    # Default prefix path should not exist on custom app
    old_prefix_response = custom_client.get("/api/v1/health")
    assert old_prefix_response.status_code == status.HTTP_404_NOT_FOUND


def test_openapi_documentation_accessible(client: TestClient) -> None:
    """Test that OpenAPI schema and Swagger UI endpoints are accessible."""
    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == status.HTTP_200_OK
    schema = openapi_res.json()
    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]

    docs_res = client.get("/docs")
    assert docs_res.status_code == status.HTTP_200_OK


def test_http_exception_handling(client: TestClient) -> None:
    """Test that HTTP errors produce structured responses without leaking internals."""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "HTTP_404"
    assert "traceback" not in str(data).lower()
    assert "password" not in str(data).lower()
    assert "secret" not in str(data).lower()


def test_custom_exception_handling() -> None:
    """Test that custom domain exceptions return consistent sanitized responses."""
    test_app = create_app()

    @test_app.get("/trigger-error")
    async def trigger_error() -> None:
        raise UntangleError(
            message="Domain failure",
            code="TEST_DOMAIN_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"reason": "test"},
        )

    @test_app.get("/trigger-unhandled")
    async def trigger_unhandled() -> None:
        raise RuntimeError("Secret DB connection failed at /var/secrets/key")

    test_client = TestClient(test_app, raise_server_exceptions=False)

    # Test domain exception handler
    res_domain = test_client.get("/trigger-error")
    assert res_domain.status_code == status.HTTP_400_BAD_REQUEST
    domain_data = res_domain.json()
    assert domain_data["status"] == "error"
    assert domain_data["error"]["code"] == "TEST_DOMAIN_ERROR"
    assert domain_data["error"]["message"] == "Domain failure"
    assert domain_data["error"]["details"] == {"reason": "test"}

    # Test unhandled exception handler - must NOT leak internal path or message
    res_unhandled = test_client.get("/trigger-unhandled")
    assert res_unhandled.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    unhandled_data = res_unhandled.json()
    assert unhandled_data["status"] == "error"
    assert unhandled_data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "Secret" not in unhandled_data["error"]["message"]
    assert "/var/secrets" not in str(unhandled_data)
