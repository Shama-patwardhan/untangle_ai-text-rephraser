"""Tests verifying text analysis on varied writing samples.

Validates:
- Reliability and lack of misleading findings on short texts.
- Reduction of false positives on ordinary human prose and technical documentation.
- Detection of genuine repetitive patterns and uniform cadence.
- Punctuation behavior with single vs. multiple em-dash pairs.
- Explanatory neutrality and avoidance of AI authorship claims.
"""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.analyzer import analyze_text

client = TestClient(app)
settings = get_settings()


def test_short_text_single_sentence() -> None:
    """Test that a single-sentence short text has no misleading findings."""
    text = "The quick brown fox jumps over the lazy dog."
    result = analyze_text(text, settings)

    assert result.statistics.sentence_count == 1
    assert result.statistics.word_count == 9
    assert result.statistics.sentence_length_std_dev == 0.0
    # No findings should trigger on a simple 9-word sentence
    assert len(result.findings) == 0
    # Summary should note brevity
    assert "very brief" in result.summary


def test_short_text_two_sentences_no_false_uniformity() -> None:
    """Test that a 2-sentence conversational note does not flag uniformity."""
    text = "Meeting is at noon. Please bring your project notes."
    result = analyze_text(text, settings)

    assert result.statistics.sentence_count == 2
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_UNIFORM_SENTENCE_LENGTH" not in rule_ids
    assert "very brief" in result.summary


def test_ordinary_human_email_no_false_positives() -> None:
    """Test that standard conversational email produces zero false-positive findings."""
    email_text = (
        "Hi Jordan, hope your week is going well. We reviewed the project drafts "
        "from yesterday and have a few small comments. Let's touch base on Thursday "
        "afternoon if you are free. Best regards, Alex."
    )
    result = analyze_text(email_text, settings)

    assert result.statistics.sentence_count == 4
    assert result.statistics.word_count > 25
    # Standard email should have no stylistic anomaly findings
    assert len(result.findings) == 0
    assert "No notable" in result.summary


def test_human_writing_with_common_connective_phrases() -> None:
    """Test that natural use of connective phrases does not trigger redundancy."""
    essay_text = (
        "We analyzed the primary sources in order to understand historical context. "
        "The researchers examined social trends as well as economic factors. "
        "In order to confirm these initial insights, the team evaluated archival "
        "records as well as recent statistical publications."
    )
    result = analyze_text(essay_text, settings)

    # 'in order to' and 'as well as' occur 2 times naturally
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_REPEATED_PHRASES" not in rule_ids


def test_technical_documentation_no_false_positives() -> None:
    """Test that technical writing with repeated domain terms is not falsely flagged."""
    tech_text = (
        "The microservice processes incoming payment requests asynchronously. "
        "After validating the cryptographic signature, it stores the transaction "
        "record in the primary database. If validation fails, an error response "
        "is returned immediately to the client with status code 400. All database "
        "operations are wrapped in an atomic transaction to ensure data integrity."
    )
    result = analyze_text(tech_text, settings)

    assert result.statistics.sentence_count == 4
    assert result.statistics.word_count > 45
    # Technical writing with diverse sentence lengths should not flag uniform cadence
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_UNIFORM_SENTENCE_LENGTH" not in rule_ids
    assert "RULE_REPETITIVE_TRANSITIONS" not in rule_ids


def test_academic_writing_sample() -> None:
    """Test that formal academic text with varied transitions is analyzed cleanly."""
    academic_text = (
        "Recent advances in natural language processing have spurred interest in "
        "automated writing evaluation. In this study, we evaluate several benchmark "
        "datasets across diverse writing tasks. Although previous methodologies "
        "demonstrated high accuracy on synthetic benchmarks, real-world deployment "
        "reveals noticeable sensitivity to domain shifts. Consequently, further "
        "investigation into robust evaluation metrics is warranted."
    )
    result = analyze_text(academic_text, settings)

    assert result.statistics.sentence_count == 4
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_REPETITIVE_TRANSITIONS" not in rule_ids
    assert "RULE_UNIFORM_SENTENCE_LENGTH" not in rule_ids


def test_repetitive_transitions_distant_occurrences_no_false_positive() -> None:
    """Test that distant transition occurrences in longer texts are not flagged."""
    sentences = [
        "Moreover, the initial phase established foundational requirements.",
        "The secondary phase expanded user authentication capabilities.",
        "Engineers integrated OAuth2 protocols into the identity provider.",
        "Database migrations ran successfully during the maintenance window.",
        "Automated regression tests verified that no breaking changes occurred.",
        "Performance benchmarks indicated sub-millisecond response latency.",
        "Documentation was updated to reflect the new authorization endpoints.",
        "Team leads reviewed the pull request and approved staging deployment.",
        "Moreover, future releases will introduce role-based access control.",
    ]
    text = " ".join(sentences)
    result = analyze_text(text, settings)

    # 'Moreover' appears at sentence 1 and sentence 9 (8 sentences apart)
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_REPETITIVE_TRANSITIONS" not in rule_ids


def test_repetitive_transitions_consecutive_triggers() -> None:
    """Test that consecutive sentences opening with the same transition are flagged."""
    text = (
        "Furthermore, the experimental group showed marked improvement. "
        "Furthermore, control subjects showed no statistically significant change. "
        "These observations confirm the original hypothesis."
    )
    result = analyze_text(text, settings)

    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_REPETITIVE_TRANSITIONS" in rule_ids
    finding = next(
        f for f in result.findings if f.rule_id == "RULE_REPETITIVE_TRANSITIONS"
    )
    assert finding.evidence["is_consecutive"] is True
    assert finding.severity == "medium"


def test_frequent_punctuation_single_em_dash_pair_no_false_positive() -> None:
    """Test single parenthetical em-dash pair does not trigger punctuation rule."""
    text = (
        "The proposed architecture — which was designed in consultation with "
        "the security team — satisfies all compliance requirements. "
        "All services are isolated within private subnets. "
        "External access is strictly mediated by the API gateway."
    )
    result = analyze_text(text, settings)

    rule_ids = [f.rule_id for f in result.findings]
    # Single em-dash pair (2 dashes) in 3 sentences should NOT be flagged as elevated
    assert "RULE_FREQUENT_PUNCTUATION" not in rule_ids


def test_frequent_punctuation_excessive_em_dashes_triggers() -> None:
    """Test that excessive em-dashes across multiple sentences trigger the finding."""
    text = (
        "The first proposal — drafted in January — outlined preliminary targets. "
        "The second iteration — finalized in March — refined the specifications. "
        "The final roadmap — approved in June — established deployment milestones."
    )
    result = analyze_text(text, settings)

    # 6 em-dashes across 3 sentences (ratio 2.0 >= 0.5)
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_FREQUENT_PUNCTUATION" in rule_ids
    finding = next(
        f for f in result.findings if f.rule_id == "RULE_FREQUENT_PUNCTUATION"
    )
    assert finding.evidence["count"] >= 3


def test_sentence_length_variation_high_variance() -> None:
    """Test that natural human prose with diverse sentence lengths has high std dev."""
    text = (
        "Time was short. "
        "The dedicated research team worked tirelessly through the night to compile "
        "all empirical observations from the twelve participating testing laboratories "
        "across three continents. "
        "Results looked promising. "
        "An exhaustive statistical examination of all gathered data points confirmed "
        "that the experimental cohort outperformed the baseline control group across "
        "every primary benchmark metric."
    )
    result = analyze_text(text, settings)

    # Sentence lengths: [3, 23, 3, 25] -> high variance
    assert result.statistics.sentence_length_std_dev > 8.0
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_UNIFORM_SENTENCE_LENGTH" not in rule_ids


def test_sentence_length_variation_uniform_cadence_triggers() -> None:
    """Test that formulaic uniform sentence lengths trigger the experimental finding."""
    text = (
        "The primary system module processes all incoming transactional data records. "
        "The secondary analytics module aggregates all monthly performance metrics. "
        "The tertiary reporting module generates all executive compliance summaries. "
        "The quaternary backup module archives all historical repository snapshots."
    )
    result = analyze_text(text, settings)

    # Sentence lengths: [10, 9, 9, 9] -> std_dev = 0.50 (low variance)
    assert result.statistics.sentence_length_std_dev <= 0.8
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE_UNIFORM_SENTENCE_LENGTH" in rule_ids


def test_no_ai_authorship_claims_in_findings_or_summary() -> None:
    """Verify that findings, evidence, and summaries never claim AI authorship."""
    test_texts = [
        "Quick test message.",
        "Furthermore, we noticed trends. Furthermore, we verified outcomes.",
        "The quick brown fox jumps over the lazy dog.",
    ]
    for text in test_texts:
        result = analyze_text(text, settings)
        summary_lower = result.summary.lower()
        assert "written by ai" not in summary_lower
        assert "ai generated" not in summary_lower
        assert "probability of ai" not in summary_lower

        for finding in result.findings:
            explanation_lower = finding.explanation.lower()
            assert "written by ai" not in explanation_lower
            assert "ai generated" not in explanation_lower
            assert "probability" not in explanation_lower
