"""Explainable heuristic pattern detectors for writing analysis.

Each detector evaluates observable stylistic patterns in text and returns
structured Finding objects with rule IDs, descriptions, observable evidence,
and severity ratings.

Rules implemented:
1. RULE_REPEATED_PHRASES: Multiword n-grams repeated above threshold.
2. RULE_UNIFORM_SENTENCE_LENGTH: Low sentence length variance (experimental).
3. RULE_REPETITIVE_TRANSITIONS: Overuse of identical sentence-initial transitions.
4. RULE_FREQUENT_PUNCTUATION: Elevated punctuation marks (experimental).
"""

import re
from collections import defaultdict
from typing import Final

from app.config import Settings
from app.schemas.analysis import Finding, RepeatedPhrase, TextSpan, TextStatistics
from app.services.statistics import SentenceSpan

# Formal discourse transitions monitored for sentence-initial repetition.
DISCOURSE_TRANSITIONS: Final[frozenset[str]] = frozenset(
    {
        "additionally",
        "as a result",
        "consequently",
        "firstly",
        "furthermore",
        "importantly",
        "in addition",
        "in conclusion",
        "in fact",
        "moreover",
        "notably",
        "on the other hand",
        "overall",
        "secondly",
        "significantly",
        "subsequently",
        "therefore",
        "to summarize",
    }
)


# Common grammatical connective phrases that occur naturally in standard prose.
COMMON_GRAMMATICAL_PHRASES: Final[frozenset[str]] = frozenset(
    {
        "as well as",
        "in order to",
        "one of the",
        "part of the",
        "due to the",
        "in terms of",
        "at the same time",
        "in addition to",
        "as a result of",
        "based on the",
        "with respect to",
        "in the case of",
        "on the basis of",
        "there is a",
        "there are a",
        "it is important",
        "it is necessary",
    }
)


def detect_repeated_phrases(
    repeated_phrases: list[RepeatedPhrase],
    min_repetitions: int = 2,
    total_words: int | None = None,
) -> list[Finding]:
    """Detect multiword phrases that repeat at or above the configured threshold.

    Filters out common grammatical connective phrases unless repeated frequently,
    reducing false positives on standard human and technical writing.

    Args:
        repeated_phrases: List of candidate repeated phrases.
        min_repetitions: Minimum occurrence threshold.
        total_words: Optional total word count of the analyzed text.

    Returns:
        List of findings for qualifying repeated phrases.
    """
    findings: list[Finding] = []

    for rp in repeated_phrases:
        if rp.count < min_repetitions:
            continue

        # Common connective phrases require >= 3 occurrences to be notable
        if rp.phrase in COMMON_GRAMMATICAL_PHRASES and rp.count < 3:
            continue

        # On very brief samples, 2 occurrences of a phrase are often topic references
        if total_words is not None and total_words < 35 and rp.count == 2:
            continue

        word_count = len(rp.phrase.split())
        severity: str = "medium" if (rp.count >= 4 or word_count >= 4) else "low"
        first_span = rp.spans[0] if rp.spans else None

        findings.append(
            Finding(
                rule_id="RULE_REPEATED_PHRASES",
                title="Repeated multiword phrase",
                explanation=(
                    f"The phrase '{rp.phrase}' appears {rp.count} times in the text. "
                    "Verbatim multiword repetition can indicate formulaic phrasing "
                    "or structural redundancy."
                ),
                severity=severity,  # type: ignore[arg-type]
                evidence={
                    "phrase": rp.phrase,
                    "count": rp.count,
                    "word_count": word_count,
                    "repetition_threshold": min_repetitions,
                    "total_spans_found": len(rp.spans),
                },
                span=first_span,
            )
        )

    return findings


def detect_uniform_sentence_length(
    sentences: list[SentenceSpan],
    lengths: list[int],
    std_dev: float,
    min_count: int = 3,
    threshold_std_dev: float = 1.5,
) -> list[Finding]:
    """Flag passages where sentence lengths exhibit unusually low standard deviation.

    This rule is labeled experimental. Human writing typically exhibits rhythmic
    variation in sentence length, but low variance is not proof of AI authorship.

    Args:
        sentences: Segmented sentence spans.
        lengths: Integer word counts per sentence.
        std_dev: Measured standard deviation of sentence lengths.
        min_count: Minimum sentence count required to evaluate.
        threshold_std_dev: Standard deviation threshold below which uniformity
            is flagged.

    Returns:
        List containing a finding if criteria are met, otherwise empty.
    """
    if len(sentences) < min_count or not lengths:
        return []

    mean_length = round(sum(lengths) / len(lengths), 2)
    # Check if sentence length variance is unusually uniform:
    # 1. Exactly identical sentence lengths (std_dev == 0.0) across sentences
    is_uniform = std_dev == 0.0 or (
        std_dev <= threshold_std_dev
        and mean_length >= 5.0
        and sum(lengths) >= 20
        and (mean_length > 0 and (std_dev / mean_length) <= 0.20)
    )

    if is_uniform:
        severity: str = "medium" if (std_dev <= 0.8 and len(sentences) >= 4) else "low"

        return [
            Finding(
                rule_id="RULE_UNIFORM_SENTENCE_LENGTH",
                title="Uniform sentence length (Experimental)",
                explanation=(
                    f"Sentence lengths show low variance with a standard deviation "
                    f"of {std_dev:.2f} words across {len(sentences)} sentences "
                    f"(mean: {mean_length:.1f} words). Uniform sentence cadence "
                    "can produce a monotonous rhythm. Note: this is an experimental "
                    "heuristic and does not indicate authorship."
                ),
                severity=severity,  # type: ignore[arg-type]
                evidence={
                    "sentence_count": len(sentences),
                    "std_dev": std_dev,
                    "mean_sentence_length": mean_length,
                    "threshold_std_dev": threshold_std_dev,
                    "heuristic_status": "experimental",
                },
                span=None,
            )
        ]

    return []


def detect_repetitive_transitions(
    sentences: list[SentenceSpan],
    min_count: int = 2,
) -> list[Finding]:
    """Detect sentences opening with identical discourse transitions.

    Args:
        sentences: Segmented sentence spans.
        min_count: Minimum occurrences of the same transition to flag.

    Returns:
        List of findings for repetitive transitions.
    """
    if len(sentences) < min_count:
        return []

    # Map transition phrase to list of (sentence_index, SentenceSpan)
    transition_matches: defaultdict[str, list[tuple[int, SentenceSpan]]] = defaultdict(
        list
    )

    for idx, span in enumerate(sentences):
        # Normalize sentence opening by stripping punctuation/quotes
        cleaned_opening = re.sub(r"^[\s\"'“‘(]+", "", span.text.lower())
        for transition in DISCOURSE_TRANSITIONS:
            # Match transition followed by comma, semicolon, colon, or whitespace
            pattern = r"^" + re.escape(transition) + r"(?:[\s,;:–—]|$)"
            if re.match(pattern, cleaned_opening):
                transition_matches[transition].append((idx, span))
                break

    findings: list[Finding] = []
    for transition, matches in sorted(
        transition_matches.items(), key=lambda item: -len(item[1])
    ):
        count = len(matches)
        if count >= min_count:
            indices = [idx + 1 for idx, _ in matches]
            first_span = matches[0][1]

            # Check if occurrences are consecutive
            is_consecutive = any(
                indices[i] == indices[i - 1] + 1 for i in range(1, len(indices))
            )

            # Avoid false positives in longer texts when two occurrences are far apart
            if (
                count == 2
                and not is_consecutive
                and len(sentences) > 6
                and (indices[1] - indices[0] > 4)
            ):
                continue

            severity: str = "medium" if (count >= 3 or is_consecutive) else "low"

            findings.append(
                Finding(
                    rule_id="RULE_REPETITIVE_TRANSITIONS",
                    title="Repetitive sentence-initial transition",
                    explanation=(
                        f"The transitional phrase '{transition}' begins {count} "
                        f"sentences (sentence numbers: {indices}). Overusing "
                        "identical transitions can lead to formulaic structure."
                    ),
                    severity=severity,  # type: ignore[arg-type]
                    evidence={
                        "transition": transition,
                        "occurrence_count": count,
                        "sentence_numbers": indices,
                        "is_consecutive": is_consecutive,
                        "threshold": min_count,
                    },
                    span=TextSpan(
                        start=first_span.start,
                        end=first_span.end,
                        text=first_span.text,
                    ),
                )
            )

    return findings


def detect_frequent_punctuation(
    punctuation_frequencies: dict[str, int],
    sentence_count: int,
    threshold_ratio: float = 0.5,
) -> list[Finding]:
    """Detect unusually elevated frequencies of specific punctuation marks.

    Monitors em-dashes (— or --) and semicolons (;). Requires at least 3 sentences
    and 3 occurrences to avoid false positives on single parenthetical em-dash pairs.

    Args:
        punctuation_frequencies: Mapping of punctuation character to frequency count.
        sentence_count: Number of sentences in the passage.
        threshold_ratio: Minimum ratio of mark occurrences per sentence.

    Returns:
        List of findings for elevated punctuation marks.
    """
    if sentence_count < 3:
        return []

    findings: list[Finding] = []

    # Check em-dashes (requires >= 3 to avoid flagging a single parenthetical pair)
    em_dash_count = punctuation_frequencies.get("—", 0) + punctuation_frequencies.get(
        "--", 0
    )
    if em_dash_count >= 3:
        ratio = em_dash_count / sentence_count
        if ratio >= threshold_ratio:
            findings.append(
                Finding(
                    rule_id="RULE_FREQUENT_PUNCTUATION",
                    title="Elevated punctuation frequency: em-dash (Experimental)",
                    explanation=(
                        f"The passage contains {em_dash_count} em-dashes across "
                        f"{sentence_count} sentences ({ratio:.2f} per sentence). "
                        "Frequent em-dash parentheticals can reflect a distinctive "
                        "or repetitive syntactic joining habit."
                    ),
                    severity="low",
                    evidence={
                        "punctuation_mark": "em-dash (— / --)",
                        "count": em_dash_count,
                        "ratio_per_sentence": round(ratio, 2),
                        "sentence_count": sentence_count,
                        "threshold_ratio": threshold_ratio,
                        "heuristic_status": "experimental",
                    },
                    span=None,
                )
            )

    # Check semicolons (requires >= 3)
    semicolon_count = punctuation_frequencies.get(";", 0)
    if semicolon_count >= 3:
        ratio = semicolon_count / sentence_count
        if ratio >= threshold_ratio:
            findings.append(
                Finding(
                    rule_id="RULE_FREQUENT_PUNCTUATION",
                    title="Elevated punctuation frequency: semicolon (Experimental)",
                    explanation=(
                        f"The semicolon ';' appears {semicolon_count} times across "
                        f"{sentence_count} sentences ({ratio:.2f} per sentence). "
                        "High semicolon density indicates repetitive compound-sentence "
                        "structures."
                    ),
                    severity="low",
                    evidence={
                        "punctuation_mark": ";",
                        "count": semicolon_count,
                        "ratio_per_sentence": round(ratio, 2),
                        "sentence_count": sentence_count,
                        "threshold_ratio": threshold_ratio,
                        "heuristic_status": "experimental",
                    },
                    span=None,
                )
            )

    return findings


def run_all_detectors(
    sentences: list[SentenceSpan],
    statistics: TextStatistics,
    settings: Settings,
) -> list[Finding]:
    """Execute all configured pattern detectors and return ordered findings.

    Args:
        sentences: Segmented sentence spans.
        statistics: Computed text statistics.
        settings: Application settings with threshold configurations.

    Returns:
        List of explainable findings.
    """
    findings: list[Finding] = []

    # 1. Repeated multiword phrases
    findings.extend(
        detect_repeated_phrases(
            repeated_phrases=statistics.repeated_phrases,
            min_repetitions=settings.min_phrase_repetitions,
            total_words=statistics.word_count,
        )
    )

    # 2. Uniform sentence length
    findings.extend(
        detect_uniform_sentence_length(
            sentences=sentences,
            lengths=statistics.sentence_lengths,
            std_dev=statistics.sentence_length_std_dev,
            min_count=settings.uniform_sentence_min_count,
            threshold_std_dev=settings.uniform_sentence_std_dev_threshold,
        )
    )

    # 3. Repetitive transitions
    findings.extend(
        detect_repetitive_transitions(
            sentences=sentences,
            min_count=settings.repetitive_transition_min_count,
        )
    )

    # 4. Elevated punctuation
    findings.extend(
        detect_frequent_punctuation(
            punctuation_frequencies=statistics.punctuation_frequencies,
            sentence_count=statistics.sentence_count,
            threshold_ratio=settings.frequent_punctuation_threshold,
        )
    )

    return findings
