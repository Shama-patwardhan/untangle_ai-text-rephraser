"""Preservation verification service for Untangle text improvement.

Ensures that text improvement suggestions rigorously check and verify:
1. Factual numbers, quantities, currency, and percentages.
2. Academic citations, brackets, and bibliographic references.
3. Named entities, acronyms, and proper nouns.
4. Polarity (negations and contractions) and epistemic certainty levels.

Never claims preservation is guaranteed when automated checks cannot establish it.
"""

import re
from typing import Final, Literal

from app.schemas.improvement import PreservationCheck

# Number pattern matching integers, decimals, thousands separators, and currencies
NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:\$|€|£)?\b\d+(?:[.,]\d+)*(?:%|\b)"
)

# Comprehensive academic citation patterns:
# Bracketed: [1], [1, 2], [1, p. 5], [Vaswani17], [Smith et al., 2020]
# Parenthetical: (Smith, 2020), (Smith & Jones, 2020), (Smith et al., 2021a)
CITATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\[[A-Za-z0-9,\s–\-.:]+\]"
    r"|\([A-Z][a-zA-Z\s&,\-]+(?:\s+et\s+al\.)?,\s*\d{4}[a-z]?(?::\s*\d+)?\)"
)

# Standard English sentence starters capitalized solely due to sentence position
COMMON_SENTENCE_STARTERS: Final[frozenset[str]] = frozenset(
    {
        "a",
        "additionally",
        "after",
        "although",
        "an",
        "as",
        "at",
        "before",
        "consequently",
        "due",
        "finally",
        "firstly",
        "for",
        "furthermore",
        "he",
        "however",
        "i",
        "if",
        "in",
        "it",
        "meanwhile",
        "moreover",
        "notably",
        "on",
        "overall",
        "secondly",
        "she",
        "subsequently",
        "that",
        "the",
        "therefore",
        "these",
        "they",
        "this",
        "those",
        "we",
        "when",
        "while",
        "you",
    }
)

# Negation tokens and common negative contractions
NEGATION_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "aren't",
        "barely",
        "can't",
        "cannot",
        "couldn't",
        "didn't",
        "doesn't",
        "don't",
        "hadn't",
        "hardly",
        "hasn't",
        "haven't",
        "isn't",
        "neither",
        "never",
        "no",
        "none",
        "nor",
        "not",
        "scarcely",
        "shouldn't",
        "wasn't",
        "weren't",
        "without",
        "won't",
        "wouldn't",
    }
)

# Common modal / epistemic certainty tokens
HIGH_CERTAINTY_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "always",
        "certainly",
        "conclusively",
        "definitely",
        "must",
        "proven",
        "proves",
        "undeniably",
        "will",
    }
)

HEDGING_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "apparently",
        "arguably",
        "could",
        "may",
        "might",
        "perhaps",
        "plausible",
        "possible",
        "possibly",
        "potential",
        "seemingly",
        "suggests",
        "tentative",
    }
)


def extract_numbers(text: str) -> set[str]:
    """Extract all numeric representations including symbols."""
    return set(NUMBER_PATTERN.findall(text))


def extract_citations(text: str) -> set[str]:
    """Extract standard academic and bracketed citations."""
    return set(CITATION_PATTERN.findall(text))


def extract_proper_nouns(text: str) -> set[str]:
    """Extract capitalized words that appear to be named entities or acronyms.

    Detects:
    1. Acronyms anywhere in text (e.g., API, AWS, NASA).
    2. Capitalized words occurring mid-sentence.
    3. Sentence-initial capitalized words that are not common English function words
       (e.g., "London", "FastAPI", "Einstein").
    """
    # Acronyms (e.g., API, NASA, HTTP, NLP)
    acronyms = set(re.findall(r"\b[A-Z]{2,}\b", text))

    # Word tokens supporting hyphens and internal apostrophes
    tokens = re.findall(r"\b[A-Za-z0-9_-]+\b", text)
    proper_entities = set()

    for i, token in enumerate(tokens):
        if not token[0].isupper():
            continue

        if i == 0:
            # First token: only consider proper noun if not a common sentence starter
            if token.lower() not in COMMON_SENTENCE_STARTERS:
                proper_entities.add(token)
        else:
            # Mid-sentence capitalized word
            if token.lower() not in {"the", "a", "an", "and", "or", "in", "to", "of"}:
                proper_entities.add(token)

    return acronyms | proper_entities


def verify_preservation(
    original: str,
    suggested: str,
    is_structural_or_open_ended: bool = False,
) -> PreservationCheck:
    """Verify factual, referential, and certainty preservation between passages.

    Args:
        original: Original text snippet or sentence.
        suggested: Proposed improved phrasing.
        is_structural_or_open_ended: Whether the suggestion is a structural rewrite
            or open-ended review where automated preservation cannot be established.

    Returns:
        PreservationCheck detailing whether key elements are intact.
    """
    details: list[str] = []
    has_warnings = False

    # 1. Number verification
    orig_numbers = extract_numbers(original)
    sugg_numbers = extract_numbers(suggested)
    missing_numbers = orig_numbers - sugg_numbers
    numbers_preserved = len(missing_numbers) == 0

    if not numbers_preserved:
        has_warnings = True
        details.append(
            f"Warning: Numeric elements missing in suggestion: "
            f"{sorted(missing_numbers)}"
        )
    elif orig_numbers:
        details.append(f"All {len(orig_numbers)} numerical values preserved.")

    # 2. Citation verification
    orig_citations = extract_citations(original)
    sugg_citations = extract_citations(suggested)
    missing_citations = orig_citations - sugg_citations
    citations_preserved = len(missing_citations) == 0

    if not citations_preserved:
        has_warnings = True
        details.append(
            f"Warning: Citations missing in suggestion: {sorted(missing_citations)}"
        )
    elif orig_citations:
        details.append(f"All {len(orig_citations)} citations preserved.")

    # 3. Proper noun / entity verification
    orig_entities = extract_proper_nouns(original)
    sugg_entities = extract_proper_nouns(suggested)
    missing_entities = orig_entities - sugg_entities
    entities_preserved = len(missing_entities) == 0

    if not entities_preserved:
        has_warnings = True
        details.append(
            f"Warning: Named entities missing in suggestion: {sorted(missing_entities)}"
        )
    elif orig_entities:
        details.append(f"All {len(orig_entities)} named entities preserved.")

    # 4. Polarity & Certainty verification
    # Tokenize words preserving negative contractions
    orig_lower = set(re.findall(r"\b\w+(?:'\w+)?\b", original.lower()))
    sugg_lower = set(re.findall(r"\b\w+(?:'\w+)?\b", suggested.lower()))

    # Check for accidental negation dropping
    orig_negations = orig_lower & NEGATION_TOKENS
    sugg_negations = sugg_lower & NEGATION_TOKENS
    certainty_preserved = True

    if orig_negations and not sugg_negations:
        certainty_preserved = False
        has_warnings = True
        details.append(
            f"Warning: Negation marker {sorted(orig_negations)} removed; "
            "verify polarity preservation."
        )

    # Check for certainty shifting (hedging -> high certainty)
    if (orig_lower & HEDGING_TOKENS) and (sugg_lower & HIGH_CERTAINTY_TOKENS):
        certainty_preserved = False
        has_warnings = True
        details.append(
            "Warning: Tentative phrasing may have been converted to high certainty."
        )

    # Check for certainty shifting (high certainty -> hedging)
    if (
        (orig_lower & HIGH_CERTAINTY_TOKENS)
        and (sugg_lower & HEDGING_TOKENS)
        and not (sugg_lower & HIGH_CERTAINTY_TOKENS)
    ):
        certainty_preserved = False
        has_warnings = True
        details.append(
            "Warning: High certainty requirement was softened into tentative phrasing."
        )

    # Determine status
    status: Literal["verified", "warnings_detected", "manual_review_required"]
    if is_structural_or_open_ended:
        status = "manual_review_required"
        details.append(
            "Automated checks cannot establish preservation for structural or "
            "open-ended rewrites; user review is required."
        )
    elif has_warnings:
        status = "warnings_detected"
    else:
        status = "verified"
        if not details:
            details.append(
                "Automated checks detected no numbers, citations, or entity drops; "
                "user review recommended to verify context-specific nuance."
            )

    return PreservationCheck(
        status=status,
        numbers_preserved=numbers_preserved,
        citations_preserved=citations_preserved,
        entities_preserved=entities_preserved,
        certainty_preserved=certainty_preserved,
        details=details,
    )
