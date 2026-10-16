"""Tests for text improvement, controlled reconstruction, and preservation."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas.improvement import ImproveResponse
from app.services.improver import improve_text
from app.services.verifier import (
    extract_citations,
    extract_numbers,
    extract_proper_nouns,
    verify_preservation,
)


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a test client with default settings."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing an isolated settings instance."""
    return Settings()


# ---------------------------------------------------------------------------
# Preservation Verifier Tests
# ---------------------------------------------------------------------------


def test_extract_numbers() -> None:
    """Test extracting numbers, decimals, percentages, and currencies."""
    text = "The node achieved 99.8% uptime in 2026, costing $500 and saving 15 pts."
    numbers = extract_numbers(text)
    assert "99.8%" in numbers
    assert "2026" in numbers
    assert "$500" in numbers
    assert "15" in numbers


def test_extract_citations() -> None:
    """Test extracting academic bracketed and parenthetical citations."""
    text = "Studies [1] and [2, 3] align with prior work (Vaswani et al., 2017)."
    citations = extract_citations(text)
    assert "[1]" in citations
    assert "[2, 3]" in citations
    assert "(Vaswani et al., 2017)" in citations


def test_extract_proper_nouns() -> None:
    """Test extracting capitalized entities and acronyms."""
    text = "We deployed FastAPI on AWS in London using Python."
    entities = extract_proper_nouns(text)
    assert "FastAPI" in entities
    assert "AWS" in entities
    assert "London" in entities
    assert "Python" in entities


def test_verify_preservation_success() -> None:
    """Test preservation verification when all facts and numbers are intact."""
    original = "In order to support Python 3.12, we deployed FastAPI [1] on AWS."
    suggested = "To support Python 3.12, we deployed FastAPI [1] on AWS."
    check = verify_preservation(original, suggested)

    assert check.numbers_preserved is True
    assert check.citations_preserved is True
    assert check.entities_preserved is True
    assert check.certainty_preserved is True


def test_verify_preservation_flags_dropped_number() -> None:
    """Test preservation verification warns when a numeric value is dropped."""
    original = "We processed 500 requests per second."
    suggested = "We processed requests rapidly."
    check = verify_preservation(original, suggested)

    assert check.numbers_preserved is False
    assert any("500" in d for d in check.details)


def test_verify_preservation_flags_dropped_citation() -> None:
    """Test preservation verification warns when a citation is dropped."""
    original = "This finding is corroborated by prior experiments [4]."
    suggested = "This finding is corroborated by prior experiments."
    check = verify_preservation(original, suggested)

    assert check.citations_preserved is False
    assert any("[4]" in d for d in check.details)


def test_verify_preservation_flags_negation_drop() -> None:
    """Test preservation verification warns if negation polarity is altered."""
    original = "The algorithm is not suitable for realtime use."
    suggested = "The algorithm is suitable for realtime use."
    check = verify_preservation(original, suggested)

    assert check.certainty_preserved is False
    assert any("Negation" in d for d in check.details)


# ---------------------------------------------------------------------------
# Redundancy Improvement Tests
# ---------------------------------------------------------------------------


def test_redundancy_reduction_in_order_to(test_settings: Settings) -> None:
    """Test replacing 'in order to' with concise 'to' and preserving casing."""
    text = (
        "In order to improve performance, developers should profile code. "
        "They should optimize algorithms in order to save resources."
    )
    res = improve_text(text, test_settings)

    assert res.total_suggestions >= 2
    red_suggestions = [s for s in res.suggestions if s.category == "redundancy"]
    assert len(red_suggestions) >= 2

    # First occurrence capitalized: "In order to" -> "To"
    assert red_suggestions[0].original_text == "In order to"
    assert red_suggestions[0].suggested_text == "To"
    assert "To" in red_suggestions[0].alternatives

    # Second occurrence lowercase: "in order to" -> "to"
    assert red_suggestions[1].original_text == "in order to"
    assert red_suggestions[1].suggested_text == "to"


def test_redundancy_reduction_multiple_phrases(test_settings: Settings) -> None:
    """Test replacing multiple different wordy phrases."""
    text = (
        "Due to the fact that the server was busy, we had to make a decision "
        "at this point in time."
    )
    res = improve_text(text, test_settings)

    categories = [s.category for s in res.suggestions]
    assert "redundancy" in categories
    original_texts = [s.original_text.lower() for s in res.suggestions]
    assert "due to the fact that" in original_texts
    assert "make a decision" in original_texts
    assert "at this point in time" in original_texts


# ---------------------------------------------------------------------------
# Repetitive Transitions Improvement Tests
# ---------------------------------------------------------------------------


def test_repetitive_transition_suggestions(test_settings: Settings) -> None:
    """Test varying consecutive repetitive transitions."""
    text = (
        "Furthermore, the frontend initiates the authentication request. "
        "Furthermore, the gateway validates the session credentials. "
        "Furthermore, the database records the audit event."
    )
    res = improve_text(text, test_settings)

    trans_suggestions = [s for s in res.suggestions if s.category == "transition"]
    assert len(trans_suggestions) >= 2
    # First occurrence remains untouched; 2nd and 3rd receive variation suggestions
    for sug in trans_suggestions:
        assert sug.rule_id == "RULE_REPETITIVE_TRANSITIONS"
        assert len(sug.alternatives) > 0
        assert sug.preservation.certainty_preserved is True


# ---------------------------------------------------------------------------
# Structural / Monotonous Sentence Cadence Tests
# ---------------------------------------------------------------------------


def test_structural_cadence_suggestions(test_settings: Settings) -> None:
    """Test suggesting sentence combination when cadence is uniform."""
    text = (
        "The primary module processes incoming data. "
        "The secondary module aggregates system metrics. "
        "The tertiary module generates summary reports. "
        "The quaternary module archives backup records."
    )
    res = improve_text(text, test_settings)

    struct_suggestions = [s for s in res.suggestions if s.category == "structure"]
    assert len(struct_suggestions) >= 1
    sug = struct_suggestions[0]
    assert sug.rule_id == "RULE_UNIFORM_SENTENCE_LENGTH"
    assert ", and" in sug.suggested_text
    assert len(sug.alternatives) >= 2


# ---------------------------------------------------------------------------
# Preview Draft Generation Tests
# ---------------------------------------------------------------------------


def test_draft_preview_generation(test_settings: Settings) -> None:
    """Test that suggested draft incorporates improvements non-destructively."""
    text = (
        "In order to complete the project, we must make a decision "
        "at this point in time."
    )
    res = improve_text(text, test_settings, include_draft_preview=True)

    assert res.suggested_draft is not None
    assert "In order to" not in res.suggested_draft
    assert "To complete the project" in res.suggested_draft
    assert "decide" in res.suggested_draft
    # Original text remains untouched
    assert res.original_text == text


def test_draft_preview_omitted_when_requested(test_settings: Settings) -> None:
    """Test draft preview can be omitted by user request."""
    text = "In order to run the build, we execute the script."
    res = improve_text(text, test_settings, include_draft_preview=False)

    assert res.suggested_draft is None
    assert len(res.suggestions) > 0


# ---------------------------------------------------------------------------
# API Endpoints Integration Tests (/improve and /reconstruct)
# ---------------------------------------------------------------------------


def test_api_improve_success(client: TestClient) -> None:
    """Test POST /api/v1/improve successfully returns structured suggestions."""
    payload = {
        "text": (
            "In order to test the pipeline, we need to make a decision. "
            "Furthermore, we must verify the database. "
            "Furthermore, we must update the cache."
        ),
        "include_draft_preview": True,
    }
    response = client.post("/api/v1/improve", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "improvement_id" in data
    assert data["improvement_id"].startswith("imp_")
    assert data["original_text"] == payload["text"]
    assert data["suggested_draft"] is not None
    assert data["total_suggestions"] > 0
    assert len(data["suggestions"]) == data["total_suggestions"]
    assert "preservation_guarantee" in data

    # Validate response adheres to Pydantic schema
    validated = ImproveResponse(**data)
    assert validated.total_suggestions == len(validated.suggestions)


def test_api_reconstruct_alias_success(client: TestClient) -> None:
    """Test POST /api/v1/reconstruct alias behaves identically to /improve."""
    payload = {
        "text": "Due to the fact that tests pass, we proceed.",
        "include_draft_preview": True,
    }
    response = client.post("/api/v1/reconstruct", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["total_suggestions"] >= 1
    assert "because" in data["suggestions"][0]["suggested_text"].lower()


def test_api_improve_empty_input_rejected(client: TestClient) -> None:
    """Test rejecting empty string with 422 Unprocessable Entity."""
    response = client.post("/api/v1/improve", json={"text": ""})
    assert response.status_code == 422


def test_api_improve_whitespace_only_rejected(client: TestClient) -> None:
    """Test rejecting whitespace-only string with 422."""
    response = client.post("/api/v1/improve", json={"text": "   \n\t  "})
    assert response.status_code == 422


def test_api_improve_oversized_text_rejected(client: TestClient) -> None:
    """Test rejecting input exceeding max length with 422 AppValidationError."""
    oversized = "a" * 20001
    response = client.post("/api/v1/improve", json={"text": oversized})
    assert response.status_code == 422
    data = response.json()
    assert "exceeds maximum" in data["error"]["message"]


def test_user_review_contract_preservation(client: TestClient) -> None:
    """Ensure suggestions are reviewable and facts/citations are verified."""
    text = (
        "In order to replicate the findings of [1], the researchers evaluated "
        "42 distinct specimens in London."
    )
    response = client.post("/api/v1/improve", json={"text": text})
    assert response.status_code == 200
    data = response.json()

    # User review guarantee present
    assert "never silently" in data["preservation_guarantee"].lower() or (
        "does not silently rewrite" in data["preservation_guarantee"]
    )

    for suggestion in data["suggestions"]:
        # Each suggestion has clear options and verification
        assert suggestion["explanation"] != ""
        assert len(suggestion["alternatives"]) >= 1
        assert suggestion["preservation"]["numbers_preserved"] is True
        assert suggestion["preservation"]["citations_preserved"] is True
        assert suggestion["preservation"]["entities_preserved"] is True
