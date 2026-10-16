"""Deterministic text statistics computation and structural segmentation.

This module provides independently testable functions for:
- Paragraph and sentence segmentation
- Tokenization and word counting
- Sentence length metrics (mean, standard deviation, distribution)
- Punctuation frequency tracking
- Repeated words and multiword phrase detection

Limitations of Sentence Segmentation:
Sentence segmentation uses rule-based heuristic pattern matching over terminal
punctuation, whitespace, and abbreviation allowlists. It handles common English
honorifics (e.g., Dr., Mr.), Latin abbreviations (e.g., e.g., i.e.), decimals,
ellipses, and quotation marks. It does not employ a statistical dependency parser
and may missegment sentences that begin with lowercase tokens or contain unusual,
domain-specific abbreviations.
"""

import re
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Final

from app.schemas.analysis import (
    RepeatedItem,
    RepeatedPhrase,
    TextSpan,
    TextStatistics,
)

# Common abbreviations that do not mark sentence endings before a period.
COMMON_ABBREVIATIONS: Final[frozenset[str]] = frozenset(
    {
        "mr.",
        "mrs.",
        "ms.",
        "dr.",
        "prof.",
        "sr.",
        "jr.",
        "vs.",
        "etc.",
        "e.g.",
        "i.e.",
        "u.s.",
        "u.k.",
        "inc.",
        "ltd.",
        "corp.",
        "co.",
        "jan.",
        "feb.",
        "mar.",
        "apr.",
        "jun.",
        "jul.",
        "aug.",
        "sep.",
        "sept.",
        "oct.",
        "nov.",
        "dec.",
        "dept.",
        "est.",
        "approx.",
        "al.",
        "no.",
        "st.",
        "a.m.",
        "p.m.",
    }
)

# Standard English stopwords to filter out from content-word repetition analysis.
ENGLISH_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "s",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "t",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
)

# Standard punctuation characters monitored for frequencies.
MONITORED_PUNCTUATION: Final[str] = ",.;:!?—–-\"'“‘’”()[]…/"


@dataclass(frozen=True, slots=True)
class SentenceSpan:
    """Represents a segmented sentence with character span bounds."""

    text: str
    start: int
    end: int


def split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs separated by double newlines.

    Args:
        text: Input string.

    Returns:
        List of trimmed paragraph strings.
    """
    if not text or not text.strip():
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs if paragraphs else [text.strip()]


def split_sentences(text: str) -> list[SentenceSpan]:
    """Segment text into individual sentences with character offsets.

    Handles abbreviations, decimal numbers, quotes, ellipses, and Unicode
    punctuation.

    Args:
        text: Input string to segment.

    Returns:
        List of SentenceSpan instances containing sentence text and bounds.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    # Regex matches candidate sentence terminal boundaries:
    # 1. ASCII (. ! ? …) followed by quotes and whitespace or end of string.
    # 2. CJK (。 ！ ？) followed by quotes, with or without whitespace.
    pattern = re.compile(
        r'([.!?…]+[\'"\u201d\u2019)\]]*)(?:\s+|\Z)|'
        r'([\u3002\uff01\uff1f]+[\'"\u201d\u2019)\]]*)(?:\s*|\Z)',
        re.UNICODE,
    )

    sentences: list[SentenceSpan] = []
    current_start = 0

    for match in pattern.finditer(text):
        if match.group(1):
            punct_end = match.end(1)
            candidate = text[current_start:punct_end].strip()

            if not candidate or not any(c.isalnum() for c in candidate):
                current_start = match.end()
                continue

            # Check if boundary dot is part of an abbreviation or initial
            last_word_match = re.search(r"(\b[A-Za-z0-9.]+)\s*$", candidate)
            if last_word_match:
                last_word = last_word_match.group(1).lower()
                if last_word in COMMON_ABBREVIATIONS and match.end() < len(text):
                    continue
                if re.match(r"^[a-zA-Z]\.$", last_word) and match.end() < len(text):
                    continue

            # If period is followed by lowercase, it is not a sentence boundary
            if "." in match.group(1) and match.end() < len(text):
                following = text[match.end() :].lstrip()
                if following and following[0].islower():
                    continue
        else:
            punct_end = match.end(2)
            candidate = text[current_start:punct_end].strip()

            if not candidate or not any(c.isalnum() for c in candidate):
                current_start = match.end()
                continue

        # Calculate exact start index of non-whitespace content
        raw_slice = text[current_start:punct_end]
        actual_start = current_start + (len(raw_slice) - len(raw_slice.lstrip()))
        sentences.append(
            SentenceSpan(
                text=candidate,
                start=actual_start,
                end=actual_start + len(candidate),
            )
        )
        current_start = match.end()

    # Capture remaining trailing text if any
    if current_start < len(text):
        trailing = text[current_start:].strip()
        if trailing and any(c.isalnum() for c in trailing):
            raw_trailing = text[current_start:]
            actual_start = current_start + (
                len(raw_trailing) - len(raw_trailing.lstrip())
            )
            sentences.append(
                SentenceSpan(
                    text=trailing,
                    start=actual_start,
                    end=actual_start + len(trailing),
                )
            )

    if sentences:
        return sentences
    if any(c.isalnum() for c in cleaned):
        return [SentenceSpan(text=cleaned, start=0, end=len(cleaned))]
    return []


def extract_words(text: str) -> list[str]:
    """Extract individual words from text, supporting Unicode and contractions.

    Args:
        text: Input string.

    Returns:
        List of extracted words.
    """
    if not text:
        return []
    return re.findall(r"\b[^\W\d_]+(?:['’\-][^\W\d_]+)*\b", text, re.UNICODE)


def calculate_sentence_lengths(sentences: list[SentenceSpan]) -> list[int]:
    """Compute word counts for each sentence in order.

    Args:
        sentences: List of SentenceSpan instances.

    Returns:
        List of integer word counts.
    """
    return [len(extract_words(s.text)) for s in sentences]


def calculate_mean_and_std_dev(lengths: list[int]) -> tuple[float, float]:
    """Calculate mean sentence length and sample standard deviation in words.

    Statistical definition:
    - Mean is the arithmetic average: sum(lengths) / N.
    - Standard deviation is the sample standard deviation with Bessel's
      correction (N - 1 degrees of freedom).
    - For samples of 0 or 1 sentence, the standard deviation is defined as 0.0.

    Args:
        lengths: List of integer sentence lengths (word counts).

    Returns:
        Tuple of (mean_length, std_dev) rounded to 2 decimal places.
    """
    if not lengths:
        return 0.0, 0.0

    mean_val = round(sum(lengths) / len(lengths), 2)
    if len(lengths) <= 1:
        return mean_val, 0.0

    # Sample standard deviation (N - 1 denominator)
    std_val = round(statistics.stdev(lengths), 2)
    return mean_val, std_val


def calculate_length_distribution(lengths: list[int]) -> dict[str, int]:
    """Group sentence lengths into standardized distribution bins.

    Bins:
        - '1-5' (very short)
        - '6-14' (short)
        - '15-25' (medium)
        - '26-40' (long)
        - '41+' (very long)

    Args:
        lengths: List of integer sentence lengths.

    Returns:
        Mapping of bin name to sentence count.
    """
    bins = {
        "1-5": 0,
        "6-14": 0,
        "15-25": 0,
        "26-40": 0,
        "41+": 0,
    }
    for length in lengths:
        if length <= 5:
            bins["1-5"] += 1
        elif length <= 14:
            bins["6-14"] += 1
        elif length <= 25:
            bins["15-25"] += 1
        elif length <= 40:
            bins["26-40"] += 1
        else:
            bins["41+"] += 1
    return bins


def calculate_punctuation_frequencies(text: str) -> dict[str, int]:
    """Count frequencies of punctuation marks present in the text.

    Args:
        text: Input string.

    Returns:
        Dictionary mapping punctuation mark to its total frequency count.
    """
    counts: dict[str, int] = {}
    for char in text:
        if char in MONITORED_PUNCTUATION:
            counts[char] = counts.get(char, 0) + 1
    # Also count double-dash "--" as a surrogate em-dash if present
    double_dashes = text.count("--")
    if double_dashes > 0:
        counts["--"] = double_dashes

    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def find_repeated_words(
    words: list[str],
    min_count: int = 3,
    min_length: int = 4,
) -> list[RepeatedItem]:
    """Identify frequently repeated content words excluding standard stopwords.

    Args:
        words: List of words.
        min_count: Minimum occurrence threshold.
        min_length: Minimum character length for candidate words.

    Returns:
        List of RepeatedItem instances sorted descending by frequency.
    """
    filtered = [
        w.lower()
        for w in words
        if len(w) >= min_length and w.lower() not in ENGLISH_STOPWORDS
    ]
    counts = Counter(filtered)
    results = [
        RepeatedItem(item=word, count=count)
        for word, count in counts.most_common()
        if count >= min_count
    ]
    return results


def find_repeated_phrases(
    text: str,
    words: list[str],
    min_phrase_words: int = 3,
    max_phrase_words: int = 5,
    min_repetitions: int = 2,
) -> list[RepeatedPhrase]:
    """Identify repeated multiword n-grams with location spans.

    Subsumes smaller sub-phrases when a longer parent phrase has the same
    occurrence count.

    Args:
        text: Original input text for span location.
        words: List of tokenized words.
        min_phrase_words: Minimum n-gram word length.
        max_phrase_words: Maximum n-gram word length.
        min_repetitions: Minimum repetitions to qualify as a repeated phrase.

    Returns:
        List of RepeatedPhrase instances.
    """
    if len(words) < min_phrase_words:
        return []

    normalized_words = [w.lower() for w in words]
    phrase_counts: dict[str, int] = {}

    for n in range(min_phrase_words, min(max_phrase_words + 1, len(words) + 1)):
        for i in range(len(normalized_words) - n + 1):
            phrase = " ".join(normalized_words[i : i + n])
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

    # Filter by repetition threshold
    qualifying = {p: c for p, c in phrase_counts.items() if c >= min_repetitions}

    # Subsumption: remove shorter phrases contained in a longer phrase
    subsumed: set[str] = set()
    sorted_phrases = sorted(
        qualifying.keys(), key=lambda p: len(p.split()), reverse=True
    )

    for i, longer in enumerate(sorted_phrases):
        for shorter in sorted_phrases[i + 1 :]:
            if shorter in longer and qualifying[shorter] == qualifying[longer]:
                subsumed.add(shorter)

    results: list[RepeatedPhrase] = []
    ordered_keys = sorted(
        sorted_phrases, key=lambda p: (-qualifying[p], -len(p.split()))
    )
    for phrase in ordered_keys:
        if phrase in subsumed:
            continue

        count = qualifying[phrase]
        # Find character spans in original text (case-insensitive)
        escaped_tokens = [re.escape(tok) for tok in phrase.split()]
        pattern = re.compile(r"\b" + r"\s+".join(escaped_tokens) + r"\b", re.IGNORECASE)
        spans: list[TextSpan] = [
            TextSpan(start=m.start(), end=m.end(), text=m.group(0))
            for m in pattern.finditer(text)
        ]

        results.append(
            RepeatedPhrase(
                phrase=phrase,
                count=count,
                spans=spans,
            )
        )

    return results


def compute_text_statistics(
    text: str,
    min_repeated_phrase_words: int = 3,
    min_phrase_repetitions: int = 2,
) -> TextStatistics:
    """Aggregate all deterministic structural and lexical statistics for text.

    Args:
        text: Input string to analyze.
        min_repeated_phrase_words: Minimum word length for repeated phrases.
        min_phrase_repetitions: Minimum occurrence threshold for repeated phrases.

    Returns:
        Populated TextStatistics instance.
    """
    paragraphs = split_paragraphs(text)
    sentences = split_sentences(text)
    words = extract_words(text)
    lengths = calculate_sentence_lengths(sentences)
    avg_len, std_dev = calculate_mean_and_std_dev(lengths)
    distribution = calculate_length_distribution(lengths)
    punct_freqs = calculate_punctuation_frequencies(text)
    repeated_words = find_repeated_words(words)
    repeated_phrases = find_repeated_phrases(
        text=text,
        words=words,
        min_phrase_words=min_repeated_phrase_words,
        min_repetitions=min_phrase_repetitions,
    )

    return TextStatistics(
        character_count=len(text),
        character_count_no_spaces=len(re.sub(r"\s+", "", text)),
        word_count=len(words),
        sentence_count=len(sentences),
        paragraph_count=len(paragraphs),
        avg_sentence_length=avg_len,
        sentence_length_std_dev=std_dev,
        sentence_lengths=lengths,
        sentence_length_distribution=distribution,
        punctuation_frequencies=punct_freqs,
        repeated_words=repeated_words,
        repeated_phrases=repeated_phrases,
    )
