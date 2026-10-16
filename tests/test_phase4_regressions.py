"""Phase 4 regression tests: semantic preservation and edge cases.

Validates that:
1. 'in order to' is protected after arrangement verbs ('must be in order to').
2. 'in addition to' prepositional clauses are not mistaken for transitions.
3. 'for the purpose of' suggests grammatical 'for' instead of 'to'.
4. 'it is important to note that' includes comma punctuation for natural syntax.
5. Negative phrases ('is not able to') concise to 'cannot' while preserving polarity.
6. Sentence cadence combination never ruins questions, acronyms, or 'I'.
7. Citations and complex numbers ('1,000,000', '$50,000') are verified.
8. Epistemic certainty shifts (hedging vs. high certainty) are caught.
9. Negative contractions ('doesn't', 'can't') are verified.
10. Preservation status honestly distinguishes 'verified' from 'manual_review_required'.
"""

import pytest

from app.config import Settings
from app.services.improver import improve_text
from app.services.verifier import (
    extract_citations,
    extract_numbers,
    extract_proper_nouns,
    verify_preservation,
)


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing default settings."""
    return Settings()


# ---------------------------------------------------------------------------
# Edge Case 1: 'in order' Denoting Arrangement vs Filler
# ---------------------------------------------------------------------------


def test_in_order_arrangement_not_flagged(test_settings: Settings) -> None:
    """Verify 'must be in order to' is NOT flagged as redundant filler."""
    text = "The financial files must be in order to pass the annual compliance audit."
    res = improve_text(text, test_settings)

    # Should not suggest replacing 'in order to' with 'to'
    in_order_suggestions = [
        s for s in res.suggestions if s.original_text.lower() == "in order to"
    ]
    assert len(in_order_suggestions) == 0


def test_keep_in_order_not_flagged(test_settings: Settings) -> None:
    """Verify 'keep in order to' is NOT flagged as redundant filler."""
    text = "Engineers keep components in order to maintain system clarity."
    res = improve_text(text, test_settings)

    in_order_suggestions = [
        s for s in res.suggestions if s.original_text.lower() == "in order to"
    ]
    assert len(in_order_suggestions) == 0


def test_in_order_to_purposive_is_flagged(test_settings: Settings) -> None:
    """Verify standard purposive 'in order to' IS flagged as redundant."""
    text = "We optimized the database queries in order to minimize query latency."
    res = improve_text(text, test_settings)

    in_order_suggestions = [
        s for s in res.suggestions if s.original_text.lower() == "in order to"
    ]
    assert len(in_order_suggestions) == 1
    assert in_order_suggestions[0].suggested_text == "to"


# ---------------------------------------------------------------------------
# Edge Case 2: 'in addition to' Preposition vs Transition
# ---------------------------------------------------------------------------


def test_in_addition_to_preposition_not_transition(test_settings: Settings) -> None:
    """Verify 'In addition to [X]' is not converted into a discourse transition."""
    text = (
        "In addition to Redis, we utilize PostgreSQL. "
        "In addition to Kafka, we deploy RabbitMQ."
    )
    res = improve_text(text, test_settings)

    # Should NOT produce transition suggestions like "Furthermore, to Redis"
    trans_suggestions = [s for s in res.suggestions if s.category == "transition"]
    assert len(trans_suggestions) == 0


def test_in_addition_standalone_transition_is_suggested(
    test_settings: Settings,
) -> None:
    """Verify 'In addition, [Clause]' transition repetition is flagged."""
    text = (
        "In addition, the server logs all requests. "
        "In addition, the server syncs the database. "
        "In addition, the server sends email alerts."
    )
    res = improve_text(text, test_settings)

    trans_suggestions = [s for s in res.suggestions if s.category == "transition"]
    assert len(trans_suggestions) >= 2


# ---------------------------------------------------------------------------
# Edge Case 3: 'for the purpose of' Grammatical Replacement
# ---------------------------------------------------------------------------


def test_for_the_purpose_of_gerund_replacement(test_settings: Settings) -> None:
    """Verify 'for the purpose of testing' becomes 'for testing', not 'to testing'."""
    text = "The harness was executed for the purpose of benchmarking latency."
    res = improve_text(text, test_settings)

    sug = next(s for s in res.suggestions if "purpose" in s.original_text.lower())
    assert sug.suggested_text == "for"
    assert "for" in sug.alternatives


# ---------------------------------------------------------------------------
# Edge Case 4: 'it is important to note that' Punctuation
# ---------------------------------------------------------------------------


def test_it_is_important_to_note_that_has_comma(test_settings: Settings) -> None:
    """Verify 'It is important to note that' suggests 'Notably, ' with comma."""
    text = "It is important to note that the cluster requires three nodes."
    res = improve_text(text, test_settings)

    sug = next(s for s in res.suggestions if "important" in s.original_text.lower())
    assert sug.suggested_text == "Notably, "
    assert "Notably, " in sug.alternatives


# ---------------------------------------------------------------------------
# Edge Case 5: Negative Phrases & Contractions
# ---------------------------------------------------------------------------


def test_is_not_able_to_becomes_cannot(test_settings: Settings) -> None:
    """Verify 'is not able to' replaces to 'cannot', preserving negation."""
    text = "The legacy parser is not able to process UTF-8 streams."
    res = improve_text(text, test_settings)

    sug = next(s for s in res.suggestions if "not able to" in s.original_text.lower())
    assert sug.suggested_text == "cannot"
    assert sug.preservation.certainty_preserved is True


def test_negation_contractions_verified() -> None:
    """Verify negative contractions like doesn't, can't, won't are tracked."""
    orig = "The cluster doesn't support unauthenticated telemetry."
    sugg_corrupt = "The cluster supports unauthenticated telemetry."
    check = verify_preservation(orig, sugg_corrupt)

    assert check.certainty_preserved is False
    assert check.status == "warnings_detected"
    assert any("Negation" in d for d in check.details)


# ---------------------------------------------------------------------------
# Edge Case 6: Cadence Combination Safety (Acronyms, Questions, Conjunctions)
# ---------------------------------------------------------------------------


def test_sentence_combining_preserves_acronyms(test_settings: Settings) -> None:
    """Verify sentence combination does not lowercase acronyms like 'AWS'."""
    text = (
        "The internal database cluster is operational. "
        "AWS handles all background storage replication. "
        "The reporting pipeline generates nightly charts. "
        "The analytics pipeline archives monthly records."
    )
    res = improve_text(text, test_settings)

    struct_suggestions = [s for s in res.suggestions if s.category == "structure"]
    if struct_suggestions:
        # If combined with AWS, AWS must remain capitalized
        sug = struct_suggestions[0]
        if "AWS" in sug.original_text:
            assert "AWS" in sug.suggested_text
            assert "aWS" not in sug.suggested_text


def test_sentence_combining_skips_questions(test_settings: Settings) -> None:
    """Verify sentences ending with '?' are never combined with ', and'."""
    text = (
        "Did the migration complete successfully? "
        "The reporting pipeline generates nightly charts. "
        "The analytics pipeline archives monthly records. "
        "The backup pipeline purges expired snapshots."
    )
    res = improve_text(text, test_settings)

    struct_suggestions = [s for s in res.suggestions if s.category == "structure"]
    for sug in struct_suggestions:
        assert "?" not in sug.original_text


def test_sentence_combining_skips_connective_starters(
    test_settings: Settings,
) -> None:
    """Verify sentence 2 starting with connective is not joined with ', and'."""
    text = (
        "The build succeeded without warnings. "
        "However the deployment failed on node two. "
        "The reporting pipeline generates nightly charts. "
        "The analytics pipeline archives monthly records."
    )
    res = improve_text(text, test_settings)

    struct_suggestions = [s for s in res.suggestions if s.category == "structure"]
    for sug in struct_suggestions:
        assert ", and however" not in sug.suggested_text.lower()


# ---------------------------------------------------------------------------
# Edge Case 7: Citations & Numbers Preservation
# ---------------------------------------------------------------------------


def test_complex_citations_and_thousands_numbers() -> None:
    """Verify multiauthor citations and numbers with commas are parsed."""
    text = (
        "According to (Smith & Jones, 2020) and [1, p. 5], "
        "the company scaled to 1,000,000 queries at $50,000 cost."
    )
    numbers = extract_numbers(text)
    assert "1,000,000" in numbers
    assert "$50,000" in numbers

    citations = extract_citations(text)
    assert "(Smith & Jones, 2020)" in citations
    assert "[1, p. 5]" in citations


def test_contextual_preservation_in_redundancy(test_settings: Settings) -> None:
    """Verify that numbers and citations in the sentence are checked."""
    text = "In order to process 2,500 transactions for [1], we scaled London nodes."
    res = improve_text(text, test_settings)

    assert len(res.suggestions) >= 1
    sug = res.suggestions[0]
    assert sug.preservation.numbers_preserved is True
    assert sug.preservation.citations_preserved is True
    assert sug.preservation.entities_preserved is True
    assert sug.preservation.status == "verified"
    assert any("2,500" in d or "numerical" in d for d in sug.preservation.details)


# ---------------------------------------------------------------------------
# Edge Case 8: Epistemic Certainty Shifts
# ---------------------------------------------------------------------------


def test_certainty_inflation_flagged() -> None:
    """Verify changing tentative 'may suggest' to 'definitely proves' is flagged."""
    orig = "The preliminary benchmarks may suggest potential degradation."
    sugg = "The preliminary benchmarks definitely proves potential degradation."
    check = verify_preservation(orig, sugg)

    assert check.certainty_preserved is False
    assert check.status == "warnings_detected"
    assert any("Tentative" in d for d in check.details)


def test_certainty_softening_flagged() -> None:
    """Verify downgrading mandatory requirement 'must' to 'might' is flagged."""
    orig = "The production server must validate SSL certificates."
    sugg = "The production server might validate SSL certificates."
    check = verify_preservation(orig, sugg)

    assert check.certainty_preserved is False
    assert check.status == "warnings_detected"
    assert any("High certainty" in d for d in check.details)


# ---------------------------------------------------------------------------
# Edge Case 9: Sentence-Initial Proper Nouns
# ---------------------------------------------------------------------------


def test_sentence_initial_proper_noun_detected() -> None:
    """Verify capitalized names at sentence start are recognized as entities."""
    text = "London hosted the summer games."
    entities = extract_proper_nouns(text)
    assert "London" in entities


# ---------------------------------------------------------------------------
# Edge Case 10: Honest Preservation Status
# ---------------------------------------------------------------------------


def test_structural_suggestion_marked_manual_review_required(
    test_settings: Settings,
) -> None:
    """Verify cadence suggestions report 'manual_review_required'."""
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
    assert sug.preservation.status == "manual_review_required"
    assert any("cannot establish preservation" in d for d in sug.preservation.details)


def test_preservation_statement_requires_user_review(test_settings: Settings) -> None:
    """Verify preservation statement emphasizes user review over false guarantees."""
    res = improve_text("In order to test, we run pytest.", test_settings)
    stmt = res.preservation_guarantee

    assert "User review is always required" in stmt
    assert "cannot establish preservation in all linguistic contexts" in stmt
