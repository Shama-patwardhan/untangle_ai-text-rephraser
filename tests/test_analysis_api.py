"""Integration and API tests for the POST /api/v1/analyze endpoint."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, create_app
from app.schemas.analysis import AnalyzeResponse
from app.services.analyzer import STANDARD_DISCLAIMER


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a TestClient for the default application."""
    return TestClient(app)


def test_analyze_success_response_structure(client: TestClient) -> None:
    """Test successful POST /api/v1/analyze with complete response validation."""
    payload = {
        "text": (
            "The initial phase of research established fundamental parameters. "
            "The subsequent phase expanded the investigative framework. "
            "The final phase verified all experimental claims rigorously."
        )
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    validated = AnalyzeResponse.model_validate(data)

    assert validated.analysis_id.startswith("ana_")
    assert validated.statistics.word_count > 0
    assert validated.statistics.sentence_count == 3
    assert validated.statistics.paragraph_count == 1
    assert validated.statistics.avg_sentence_length > 0
    assert len(validated.statistics.sentence_lengths) == 3
    assert validated.disclaimer == STANDARD_DISCLAIMER
    assert "Analysis of" in validated.summary


def test_analyze_empty_input_rejected(client: TestClient) -> None:
    """Test that empty string input is rejected with HTTP 422."""
    response = client.post("/api/v1/analyze", json={"text": ""})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data["status"] == "error"


def test_analyze_whitespace_only_rejected(client: TestClient) -> None:
    """Test that whitespace-only input is rejected with HTTP 422."""
    response = client.post("/api/v1/analyze", json={"text": "   \n\t   "})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data["status"] == "error"


def test_analyze_missing_field_rejected(client: TestClient) -> None:
    """Test that missing required 'text' field is rejected with HTTP 422."""
    response = client.post("/api/v1/analyze", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data["status"] == "error"


def test_analyze_invalid_types_rejected(client: TestClient) -> None:
    """Test that non-string 'text' input types are rejected with HTTP 422."""
    response = client.post("/api/v1/analyze", json={"text": 12345})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response_null = client.post("/api/v1/analyze", json={"text": None})
    assert response_null.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_analyze_forbids_extra_fields(client: TestClient) -> None:
    """Test that extra unmapped request fields are rejected."""
    payload = {"text": "Valid text input.", "unexpected_field": "disallowed"}
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_analyze_oversized_text_rejected() -> None:
    """Test that text exceeding configured max_text_length is rejected with HTTP 422."""
    custom_settings = Settings(max_text_length=50)
    custom_app = create_app(settings=custom_settings)
    custom_client = TestClient(custom_app)

    long_text = "This sentence is longer than the configured fifty character limit."
    assert len(long_text) > 50

    response = custom_client.post("/api/v1/analyze", json={"text": long_text})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data["status"] == "error"
    assert "exceeds maximum allowed limit" in data["error"]["message"]


def test_analyze_custom_api_prefix() -> None:
    """Test that the analyze route respects a custom api_prefix."""
    custom_settings = Settings(api_prefix="/api/v2")
    custom_app = create_app(settings=custom_settings)
    custom_client = TestClient(custom_app)

    payload = {"text": "Testing with a custom API route prefix."}
    response = custom_client.post("/api/v2/analyze", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["statistics"]["word_count"] > 0

    # Old route should 404
    old_response = custom_client.post("/api/v1/analyze", json=payload)
    assert old_response.status_code == status.HTTP_404_NOT_FOUND


def test_analyze_detects_observable_patterns(client: TestClient) -> None:
    """Test that synthetic text with known patterns produces expected findings."""
    synthetic_passage = (
        "Furthermore, in the rapid development we observe steady results. "
        "Furthermore, in the rapid development we notice consistent data. "
        "Furthermore, in the rapid development we achieve similar outcomes."
    )
    response = client.post("/api/v1/analyze", json={"text": synthetic_passage})
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    findings = data["findings"]
    rule_ids = [f["rule_id"] for f in findings]

    assert "RULE_REPEATED_PHRASES" in rule_ids
    assert "RULE_REPETITIVE_TRANSITIONS" in rule_ids
    assert "RULE_UNIFORM_SENTENCE_LENGTH" in rule_ids

    # Verify no AI probability claim is present in findings
    for finding in findings:
        explanation = finding["explanation"].lower()
        assert "ai generated" not in explanation
        assert "proven to be ai" not in explanation


def test_openapi_contains_analyze_endpoint(client: TestClient) -> None:
    """Test that the OpenAPI documentation includes the analyze path."""
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert "/api/v1/analyze" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/analyze"]
