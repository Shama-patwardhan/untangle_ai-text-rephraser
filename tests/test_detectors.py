"""Unit tests for explainable pattern detectors."""

from app.config import Settings
from app.schemas.analysis import RepeatedPhrase, TextSpan
from app.services.detectors import (
    detect_frequent_punctuation,
    detect_repeated_phrases,
    detect_repetitive_transitions,
    detect_uniform_sentence_length,
    run_all_detectors,
)
from app.services.statistics import SentenceSpan, compute_text_statistics


def test_detect_repeated_phrases_qualifying() -> None:
    """Test repeated phrases detector flags phrases meeting repetition threshold."""
    phrases = [
        RepeatedPhrase(
            phrase="in the beginning",
            count=3,
            spans=[
                TextSpan(start=0, end=16, text="In the beginning"),
                TextSpan(start=50, end=66, text="in the beginning"),
                TextSpan(start=100, end=116, text="in the beginning"),
            ],
        ),
        RepeatedPhrase(
            phrase="a single occurrence phrase",
            count=1,
            spans=[],
        ),
    ]

    findings = detect_repeated_phrases(phrases, min_repetitions=2)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "RULE_REPEATED_PHRASES"
    assert f.title == "Repeated multiword phrase"
    assert f.evidence["count"] == 3
    assert f.span is not None
    assert f.span.start == 0


def test_detect_repeated_phrases_severity() -> None:
    """Test severity classification for repeated phrases."""
    # 3-word phrase repeated 2 times -> low severity
    p_low = [
        RepeatedPhrase(
            phrase="one two three",
            count=2,
            spans=[TextSpan(start=0, end=13, text="one two three")],
        )
    ]
    f_low = detect_repeated_phrases(p_low, min_repetitions=2)
    assert f_low[0].severity == "low"

    # 4-word phrase repeated 2 times -> medium severity
    p_med_length = [
        RepeatedPhrase(
            phrase="one two three four",
            count=2,
            spans=[TextSpan(start=0, end=18, text="one two three four")],
        )
    ]
    f_med_length = detect_repeated_phrases(p_med_length, min_repetitions=2)
    assert f_med_length[0].severity == "medium"

    # Repeated 4 times -> medium severity
    p_med_count = [
        RepeatedPhrase(
            phrase="one two three",
            count=4,
            spans=[TextSpan(start=0, end=13, text="one two three")],
        )
    ]
    f_med_count = detect_repeated_phrases(p_med_count, min_repetitions=2)
    assert f_med_count[0].severity == "medium"


def test_detect_uniform_sentence_length_triggers() -> None:
    """Test uniform sentence length flags low standard deviation."""
    sentences = [
        SentenceSpan(text="Sentence one here.", start=0, end=18),
        SentenceSpan(text="Sentence two here.", start=19, end=37),
        SentenceSpan(text="Sentence three on.", start=38, end=56),
    ]
    lengths = [3, 3, 3]
    std_dev = 0.0

    findings = detect_uniform_sentence_length(
        sentences=sentences,
        lengths=lengths,
        std_dev=std_dev,
        min_count=3,
        threshold_std_dev=1.5,
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "RULE_UNIFORM_SENTENCE_LENGTH"
    assert "Experimental" in f.title
    assert f.evidence["heuristic_status"] == "experimental"
    assert f.evidence["std_dev"] == 0.0


def test_detect_uniform_sentence_length_does_not_trigger() -> None:
    """Test uniform detector requires minimum sentences and low variance."""
    # Too few sentences (only 2)
    sentences_two = [
        SentenceSpan(text="Short sentence.", start=0, end=15),
        SentenceSpan(text="Short sentence.", start=16, end=31),
    ]
    f_two = detect_uniform_sentence_length(
        sentences=sentences_two,
        lengths=[2, 2],
        std_dev=0.0,
        min_count=3,
        threshold_std_dev=1.5,
    )
    assert len(f_two) == 0

    # High standard deviation
    sentences_diverse = [
        SentenceSpan(text="Very short.", start=0, end=11),
        SentenceSpan(text="This is a medium length sentence.", start=12, end=45),
        SentenceSpan(
            text="This is an unusually long and elaborate sentence with many words.",
            start=46,
            end=111,
        ),
    ]
    f_diverse = detect_uniform_sentence_length(
        sentences=sentences_diverse,
        lengths=[2, 6, 11],
        std_dev=4.51,
        min_count=3,
        threshold_std_dev=1.5,
    )
    assert len(f_diverse) == 0


def test_detect_repetitive_transitions_triggers() -> None:
    """Test repetitive transitions detector flags repeated sentence starters."""
    sentences = [
        SentenceSpan(text="Moreover, the experiment succeeded.", start=0, end=35),
        SentenceSpan(text="We observed clear outcomes.", start=36, end=63),
        SentenceSpan(text="Moreover, further testing confirmed it.", start=64, end=103),
    ]

    findings = detect_repetitive_transitions(sentences, min_count=2)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "RULE_REPETITIVE_TRANSITIONS"
    assert f.evidence["transition"] == "moreover"
    assert f.evidence["occurrence_count"] == 2
    assert f.evidence["sentence_numbers"] == [1, 3]
    assert f.span is not None


def test_detect_repetitive_transitions_does_not_trigger() -> None:
    """Test repetitive transitions detector ignores unique sentence starters."""
    sentences = [
        SentenceSpan(text="Moreover, we noticed changes.", start=0, end=29),
        SentenceSpan(text="However, they were minor.", start=30, end=55),
        SentenceSpan(text="Finally, the project concluded.", start=56, end=87),
    ]

    findings = detect_repetitive_transitions(sentences, min_count=2)
    assert len(findings) == 0


def test_detect_frequent_punctuation_triggers() -> None:
    """Test frequent punctuation detector flags high em-dash and semicolon counts."""
    # 3 em-dashes across 3 sentences -> ratio 1.0 (>= 0.5 threshold)
    freqs = {"—": 3, ",": 2, ".": 3}
    findings = detect_frequent_punctuation(
        punctuation_frequencies=freqs,
        sentence_count=3,
        threshold_ratio=0.5,
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "RULE_FREQUENT_PUNCTUATION"
    assert "em-dash" in f.title
    assert f.evidence["heuristic_status"] == "experimental"

    # Semicolons
    freqs_semi = {";": 3, ".": 3}
    f_semi = detect_frequent_punctuation(
        punctuation_frequencies=freqs_semi,
        sentence_count=3,
        threshold_ratio=0.5,
    )
    assert len(f_semi) == 1
    assert "semicolon" in f_semi[0].title


def test_detect_frequent_punctuation_does_not_trigger_low_density() -> None:
    """Test frequent punctuation detector ignores low punctuation density."""
    freqs = {"—": 1, ",": 5, ".": 10}
    findings = detect_frequent_punctuation(
        punctuation_frequencies=freqs,
        sentence_count=10,
        threshold_ratio=0.5,
    )
    assert len(findings) == 0


def test_run_all_detectors_integration() -> None:
    """Test running all detectors together through orchestration."""
    text = (
        "Furthermore, in the rapid development we observed progress. "
        "Furthermore, in the rapid development we maintained focus. "
        "Furthermore, in the rapid development we concluded trials."
    )
    stats = compute_text_statistics(text)
    from app.services.statistics import split_sentences

    sentences = split_sentences(text)
    settings = Settings()

    findings = run_all_detectors(
        sentences=sentences,
        statistics=stats,
        settings=settings,
    )
    rule_ids = {f.rule_id for f in findings}
    # Should flag repetitive transitions and repeated phrases
    assert "RULE_REPETITIVE_TRANSITIONS" in rule_ids
    assert "RULE_REPEATED_PHRASES" in rule_ids
