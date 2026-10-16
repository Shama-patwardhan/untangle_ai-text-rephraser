"""Text improvement service generating reviewable suggestions.

Coordinates with the writing analysis engine to identify opportunities to:
1. Remove redundant, wordy, or padding phrasing without distorting grammar.
2. Reduce unnecessary repetition of multiword phrases.
3. Vary repetitive sentence-initial discourse transitions.
4. Improve monotonous sentence structure and cadence.

Every suggestion is verified for factual, entity, citation, and certainty preservation.
Never claims preservation is guaranteed when automated checks cannot establish it.
Suggestions are structured for explicit user review, never silently altering text.
"""

import re
import uuid
from typing import Final

from app.config import Settings
from app.schemas.analysis import TextSpan
from app.schemas.improvement import (
    ImprovementSuggestion,
    ImproveResponse,
)
from app.services.analyzer import analyze_text
from app.services.statistics import SentenceSpan, split_sentences
from app.services.verifier import (
    COMMON_SENTENCE_STARTERS,
    extract_citations,
    extract_numbers,
    verify_preservation,
)

PRESERVATION_STATEMENT: Final[str] = (
    "Untangle does not silently rewrite text. All suggestions are reviewable "
    "recommendations designed to improve clarity, cadence, and conciseness. "
    "Automated checks verify the presence of numbers, citations, named entities, "
    "and polarity markers, but cannot establish preservation in all linguistic "
    "contexts. User review is always required."
)

# Comprehensive catalog of redundant/wordy phrases mapped to concise alternatives
# Sorted logically with longer phrases first to prevent subphrase collision
# Format: phrase -> (preferred_replacement, list_of_alternatives, rationale)
REDUNDANT_PHRASES: Final[dict[str, tuple[str, list[str], str]]] = {
    "it is important to note that": (
        "notably, ",
        ["notably, ", "importantly, "],
        "Replace wordy metadiscourse filler with direct adverb.",
    ),
    "due to the fact that": (
        "because",
        ["because", "since", "as"],
        "Replace wordy causal phrase 'due to the fact that' with 'because'.",
    ),
    "at this point in time": (
        "currently",
        ["now", "currently", "at present"],
        "Replace wordy temporal cliché 'at this point in time' with direct adverb.",
    ),
    "in spite of the fact that": (
        "although",
        ["although", "even though"],
        "Replace wordy concession phrase with direct conjunction 'although'.",
    ),
    "until such time as": (
        "until",
        ["until", "before"],
        "Replace bureaucratic phrasing 'until such time as' with direct 'until'.",
    ),
    "with the exception of": (
        "except for",
        ["except for", "excluding", "aside from"],
        "Replace formal circumlocution with 'except for'.",
    ),
    "in close proximity to": (
        "near",
        ["near", "close to"],
        "Replace spatial padding 'in close proximity to' with 'near'.",
    ),
    "for the purpose of": (
        "for",
        ["for", "with the aim of"],
        "Replace wordy prepositional phrase with concise preposition 'for'.",
    ),
    "as a consequence of": (
        "because of",
        ["because of", "due to"],
        "Replace bulky connective with direct preposition 'because of'.",
    ),
    "in order not to": (
        "so as not to",
        ["so as not to", "to avoid"],
        "Replace wordy negative purpose phrase 'in order not to'.",
    ),
    "in the event that": (
        "if",
        ["if", "should"],
        "Replace wordy conditional phrase 'in the event that' with 'if'.",
    ),
    "in the near future": (
        "soon",
        ["soon", "shortly"],
        "Replace wordy temporal phrase with concise adverb 'soon'.",
    ),
    "take into consideration": (
        "consider",
        ["consider", "take account of"],
        "Replace nominalized verb construction with direct verb 'consider'.",
    ),
    "make a decision": (
        "decide",
        ["decide", "make a choice"],
        "Replace smothered verb 'make a decision' with direct verb 'decide'.",
    ),
    "is not able to": (
        "cannot",
        ["cannot", "is unable to"],
        "Replace wordy negative circumlocution 'is not able to' with 'cannot'.",
    ),
    "are not able to": (
        "cannot",
        ["cannot", "are unable to"],
        "Replace wordy negative circumlocution 'are not able to' with 'cannot'.",
    ),
    "is able to": (
        "can",
        ["can", "is capable of"],
        "Replace circumlocution 'is able to' with active modal 'can'.",
    ),
    "are able to": (
        "can",
        ["can", "are capable of"],
        "Replace circumlocution 'are able to' with active modal 'can'.",
    ),
    "has the ability to": (
        "can",
        ["can", "is capable of"],
        "Replace wordy 'has the ability to' with concise modal 'can'.",
    ),
    "have the ability to": (
        "can",
        ["can", "is capable of"],
        "Replace wordy 'have the ability to' with concise modal 'can'.",
    ),
    "a large number of": (
        "many",
        ["many", "numerous"],
        "Replace wordy quantifier 'a large number of' with 'many'.",
    ),
    "a majority of": (
        "most",
        ["most", "the majority of"],
        "Replace wordy phrase 'a majority of' with concise 'most'.",
    ),
    "prior to": (
        "before",
        ["before", "prior to"],
        "Replace stiff preposition 'prior to' with natural 'before'.",
    ),
    "subsequent to": (
        "after",
        ["after", "following"],
        "Replace bureaucratic 'subsequent to' with direct 'after'.",
    ),
    "it is necessary to": (
        "must",
        ["must", "need to", "should"],
        "Replace impersonal dummy subject with direct modal 'must'.",
    ),
    "in order to": (
        "to",
        ["to", "so as to"],
        "Replace wordy filler 'in order to' with concise infinitive 'to'.",
    ),
}

# Transition variation alternatives
TRANSITION_ALTERNATIVES: Final[dict[str, list[str]]] = {
    "furthermore": ["Additionally", "Moreover", "In addition", "Also"],
    "moreover": ["Furthermore", "In addition", "Additionally", "Also"],
    "additionally": ["Furthermore", "Moreover", "In addition", "Also"],
    "consequently": ["As a result", "Therefore", "Thus"],
    "therefore": ["Consequently", "Thus", "As a result"],
    "in addition": ["Furthermore", "Moreover", "Additionally"],
}

# Discourse connectives that should not be prepended with ', and'
CONNECTIVE_STARTERS: Final[frozenset[str]] = frozenset(
    {
        "additionally",
        "also",
        "although",
        "and",
        "but",
        "consequently",
        "furthermore",
        "however",
        "moreover",
        "or",
        "so",
        "therefore",
        "yet",
    }
)


def _match_casing(reference: str, text: str) -> str:
    """Match the casing of reference text on replacement text."""
    if not reference or not text:
        return text
    if reference.isupper():
        return text.upper()
    if reference[0].isupper():
        return text[0].upper() + text[1:]
    return text[0].lower() + text[1:]


def _find_containing_sentence(
    start: int,
    end: int,
    sentences: list[SentenceSpan],
) -> SentenceSpan | None:
    """Find the sentence span containing the given character range."""
    for s in sentences:
        if s.start <= start and end <= s.end:
            return s
    return None


def find_redundancy_suggestions(
    text: str,
    sentences: list[SentenceSpan],
) -> list[ImprovementSuggestion]:
    """Identify opportunities to remove redundant and wordy phrasing.

    Defensively checks:
    - Protects 'in order to' after arrangement verbs (e.g., 'be/keep/put in order').
    - Checks containing sentence for context-aware factual and entity preservation.
    """
    suggestions: list[ImprovementSuggestion] = []

    for phrase, (replacement, alts, explanation) in REDUNDANT_PHRASES.items():
        escaped_phrase = re.escape(phrase)
        pattern = re.compile(rf"\b{escaped_phrase}\b", re.IGNORECASE)

        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            matched_text = text[start:end]

            # Defensive filter: protect 'in order to' after arrangement verbs
            if phrase == "in order to":
                prefix = text[max(0, start - 50) : start]
                is_be_order = bool(
                    re.search(
                        r"\b(?:be|been|being|is|are|was|were)\s+(?:all\s+)?$",
                        prefix,
                        re.IGNORECASE,
                    )
                )
                is_keep_order = bool(
                    re.search(
                        r"\b(?:keep|keeps|kept|put|puts|set|sets)\s+[\w\s]{1,30}\s+$",
                        prefix,
                        re.IGNORECASE,
                    )
                )
                if is_be_order or is_keep_order:
                    continue

            # Preserve casing
            cased_replacement = _match_casing(matched_text, replacement)
            cased_alts = [_match_casing(matched_text, alt) for alt in alts]

            # Contextual preservation verification on containing sentence
            containing_sentence = _find_containing_sentence(start, end, sentences)
            if containing_sentence:
                rel_start = start - containing_sentence.start
                rel_end = end - containing_sentence.start
                orig_sentence_text = containing_sentence.text
                suggested_sentence_text = (
                    orig_sentence_text[:rel_start]
                    + cased_replacement
                    + orig_sentence_text[rel_end:]
                )
                preservation = verify_preservation(
                    original=orig_sentence_text,
                    suggested=suggested_sentence_text,
                )
            else:
                preservation = verify_preservation(
                    original=matched_text,
                    suggested=cased_replacement,
                )

            suggestion_id = f"sug_red_{uuid.uuid4().hex[:8]}"
            suggestions.append(
                ImprovementSuggestion(
                    suggestion_id=suggestion_id,
                    rule_id="RULE_REDUNDANT_PHRASING",
                    category="redundancy",
                    title="Replace redundant phrase with concise alternative",
                    original_text=matched_text,
                    suggested_text=cased_replacement,
                    alternatives=cased_alts,
                    span=TextSpan(start=start, end=end, text=matched_text),
                    explanation=explanation,
                    preservation=preservation,
                )
            )

    return sorted(suggestions, key=lambda s: s.span.start)


def find_transition_suggestions(
    sentences: list[SentenceSpan],
    text: str,
) -> list[ImprovementSuggestion]:
    """Suggest varied discourse transitions when repetitive transitions occur.

    Filters out prepositional 'in addition to' to prevent ungrammatical edits.
    """
    suggestions: list[ImprovementSuggestion] = []
    transition_occurrences: dict[str, list[tuple[int, SentenceSpan]]] = {}

    for idx, s in enumerate(sentences):
        match = re.match(
            r"^\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)(?:,\s*|\s+)",
            s.text,
        )
        if match:
            first_phrase = match.group(1).lower().strip()

            # Filter: 'in addition to' is a prepositional phrase, not a transition
            if first_phrase == "in addition":
                remainder = s.text[match.end() :].lstrip()
                if remainder.lower().startswith("to ") or remainder.lower() == "to":
                    continue

            if first_phrase in TRANSITION_ALTERNATIVES:
                transition_occurrences.setdefault(first_phrase, []).append((idx, s))

    # For transitions appearing >= 2 times, suggest variations for 2nd+ occurrences
    for trans, occurrences in transition_occurrences.items():
        if len(occurrences) < 2:
            continue

        for _, s in occurrences[1:]:
            match = re.search(
                rf"\b{re.escape(trans)}\b(?:,\s*)?",
                s.text,
                re.IGNORECASE,
            )
            if not match:
                continue

            orig_transition_with_comma = match.group(0)
            trans_start = s.start + match.start()
            trans_end = s.start + match.end()
            orig_text = text[trans_start:trans_end]

            alt_options = TRANSITION_ALTERNATIVES.get(trans, ["Additionally"])
            has_comma = "," in orig_transition_with_comma
            suffix = ", " if has_comma else " "

            suggested = f"{alt_options[0]}{suffix}"
            alternatives = [f"{alt}{suffix}" for alt in alt_options]

            # Contextual preservation on the sentence
            rel_start = match.start()
            rel_end = match.end()
            suggested_sent = s.text[:rel_start] + suggested + s.text[rel_end:]

            preservation = verify_preservation(
                original=s.text,
                suggested=suggested_sent,
            )
            suggestion_id = f"sug_tra_{uuid.uuid4().hex[:8]}"

            suggestions.append(
                ImprovementSuggestion(
                    suggestion_id=suggestion_id,
                    rule_id="RULE_REPETITIVE_TRANSITIONS",
                    category="transition",
                    title="Vary repetitive sentence transition",
                    original_text=orig_text,
                    suggested_text=suggested,
                    alternatives=alternatives,
                    span=TextSpan(start=trans_start, end=trans_end, text=orig_text),
                    explanation=(
                        f"The transition '{trans}' is repeated multiple times. "
                        "Varying transition choices prevents monotonous discourse flow."
                    ),
                    preservation=preservation,
                )
            )

    return suggestions


def find_repetition_suggestions(
    findings_list: list,
    text: str,
) -> list[ImprovementSuggestion]:
    """Generate suggestions to reduce repeated multiword phrases."""
    suggestions: list[ImprovementSuggestion] = []

    for f in findings_list:
        if f.rule_id != "RULE_REPEATED_PHRASES":
            continue

        phrase = f.evidence.get("phrase", "")
        occurrences = f.evidence.get("spans", [])
        if not phrase or len(occurrences) < 2:
            continue

        for occ in occurrences[1:]:
            start = occ.get("start", 0)
            end = occ.get("end", 0)
            occ_text = text[start:end]

            suggestion_id = f"sug_rep_{uuid.uuid4().hex[:8]}"
            explanation = (
                f"The phrase '{phrase}' repeats {len(occurrences)} times. "
                "Consider varying this occurrence with a concise reference "
                "or pronoun to reduce verbatim repetition."
            )

            # Open-ended repetition review cannot establish automated preservation
            preservation = verify_preservation(
                original=occ_text,
                suggested=phrase,
                is_structural_or_open_ended=True,
            )

            suggestions.append(
                ImprovementSuggestion(
                    suggestion_id=suggestion_id,
                    rule_id="RULE_REPEATED_PHRASES",
                    category="repetition",
                    title="Reduce repeated phrase",
                    original_text=occ_text,
                    suggested_text=f"[Review: vary or tighten '{phrase}']",
                    alternatives=[
                        f"[Review: vary or tighten '{phrase}']",
                        "[Omit or replace with pronoun]",
                    ],
                    span=TextSpan(start=start, end=end, text=occ_text),
                    explanation=explanation,
                    preservation=preservation,
                )
            )

    return suggestions


def find_structural_suggestions(
    sentences: list[SentenceSpan],
    findings_list: list,
    text: str,
) -> list[ImprovementSuggestion]:
    """Suggest structural rhythm improvements when sentence length is uniform.

    Defensively verifies:
    - Only combines if first sentence ends with '.' (avoids questions/exclamations).
    - Avoids combining if second sentence starts with a conjunction or transition.
    - Preserves capitalized acronyms, names, and 'I' at start of second sentence.
    """
    suggestions: list[ImprovementSuggestion] = []

    has_uniformity = any(
        f.rule_id == "RULE_UNIFORM_SENTENCE_LENGTH" for f in findings_list
    )
    if not has_uniformity or len(sentences) < 2:
        return suggestions

    for i in range(len(sentences) - 1):
        s1 = sentences[i]
        s2 = sentences[i + 1]

        # Defensive check: only combine statements ending with period
        if not s1.text.strip().endswith("."):
            continue

        s2_stripped = s2.text.strip()
        s2_first_word = re.split(r"\W+", s2_stripped)[0].lower() if s2_stripped else ""

        # Avoid combining if second sentence already starts with a connective
        if s2_first_word in CONNECTIVE_STARTERS:
            continue

        w1 = len(re.findall(r"\b\w+\b", s1.text))
        w2 = len(re.findall(r"\b\w+\b", s2.text))

        if 4 <= w1 <= 14 and 4 <= w2 <= 14 and abs(w1 - w2) <= 3:
            s1_clean = s1.text.rstrip(". ")
            if not s2_stripped:
                continue

            # Check if second sentence starts with an entity/acronym/'I'
            first_token_match = re.match(r"^([A-Za-z0-9_-]+)", s2_stripped)
            first_token = first_token_match.group(1) if first_token_match else ""

            should_keep_capitalized = (
                first_token == "I"
                or (len(first_token) >= 2 and first_token.isupper())
                or (first_token.lower() not in COMMON_SENTENCE_STARTERS)
            )

            if should_keep_capitalized:
                s2_cased = s2_stripped
            else:
                s2_cased = s2_stripped[0].lower() + s2_stripped[1:]

            suggested_combined = f"{s1_clean}, and {s2_cased}"
            combined_span = TextSpan(
                start=s1.start,
                end=s2.end,
                text=text[s1.start : s2.end],
            )

            # Open-ended structural changes require human review
            preservation = verify_preservation(
                original=combined_span.text,
                suggested=suggested_combined,
                is_structural_or_open_ended=True,
            )
            suggestion_id = f"sug_str_{uuid.uuid4().hex[:8]}"

            suggestions.append(
                ImprovementSuggestion(
                    suggestion_id=suggestion_id,
                    rule_id="RULE_UNIFORM_SENTENCE_LENGTH",
                    category="structure",
                    title="Combine adjacent sentences to vary cadence",
                    original_text=combined_span.text,
                    suggested_text=suggested_combined,
                    alternatives=[
                        suggested_combined,
                        f"{s1_clean}; {s2_stripped}",
                    ],
                    span=combined_span,
                    explanation=(
                        f"Adjacent sentences have similar lengths "
                        f"({w1} and {w2} words). "
                        "Combining them or varying structure creates natural cadence."
                    ),
                    preservation=preservation,
                )
            )
            break

    return suggestions


def generate_draft_preview(
    text: str,
    suggestions: list[ImprovementSuggestion],
) -> str:
    """Generate a preview draft applying non-conflicting suggestions.

    Applies redundancy replacements and transition variations in reverse order of
    start offsets. Validates that full-text numbers and citations remain intact.
    """
    applicable = [
        s
        for s in suggestions
        if s.category in {"redundancy", "transition"}
        and not s.suggested_text.startswith("[Review:")
        and s.preservation.numbers_preserved
        and s.preservation.citations_preserved
    ]

    applicable.sort(key=lambda s: s.span.start, reverse=True)

    result = text
    last_applied_start = len(text) + 1

    for s in applicable:
        if (
            s.span.end <= last_applied_start
            and result[s.span.start : s.span.end] == s.original_text
        ):
            candidate = result[: s.span.start] + s.suggested_text + result[s.span.end :]
            # Document-level preservation safety check for numbers & citations
            if extract_numbers(text) <= extract_numbers(
                candidate
            ) and extract_citations(text) <= extract_citations(candidate):
                result = candidate
                last_applied_start = s.span.start

    return result


def improve_text(
    text: str,
    settings: Settings,
    include_draft_preview: bool = True,
) -> ImproveResponse:
    """Analyze text and generate reviewable improvement suggestions.

    Args:
        text: Input text to analyze and improve.
        settings: Application settings.
        include_draft_preview: Whether to include non-destructive draft preview.

    Returns:
        ImproveResponse with suggestions, summary, and preservation statement.
    """
    # 1. Deterministic analysis and sentence segmentation
    analysis = analyze_text(text=text, settings=settings)
    sentences = split_sentences(text)

    # 2. Gather suggestions across categories
    suggestions: list[ImprovementSuggestion] = []

    # Category A: Redundancy / Wordiness removal
    suggestions.extend(find_redundancy_suggestions(text, sentences))

    # Category B: Repetitive discourse transitions
    suggestions.extend(find_transition_suggestions(sentences, text))

    # Category C: Repeated multiword phrases
    suggestions.extend(find_repetition_suggestions(analysis.findings, text))

    # Category D: Monotonous sentence structure / cadence
    suggestions.extend(find_structural_suggestions(sentences, analysis.findings, text))

    # Sort all suggestions by start offset
    suggestions.sort(key=lambda s: s.span.start)

    # 3. Generate draft preview if requested
    draft_preview: str | None = None
    if include_draft_preview and suggestions:
        draft_preview = generate_draft_preview(text, suggestions)

    # 4. Summary
    if not suggestions:
        summary = (
            "No immediate opportunities to reduce redundancy, repetition, "
            "or monotonous sentence structure were identified under current thresholds."
        )
    else:
        cats = [s.category for s in suggestions]
        cat_counts = {c: cats.count(c) for c in set(cats)}
        breakdown = ", ".join(
            f"{count} {cat}" for cat, count in sorted(cat_counts.items())
        )
        summary = (
            f"Identified {len(suggestions)} reviewable improvement opportunity(ies) "
            f"({breakdown})."
        )

    improvement_id = f"imp_{uuid.uuid4().hex[:12]}"

    return ImproveResponse(
        improvement_id=improvement_id,
        original_text=text,
        suggested_draft=draft_preview,
        suggestions=suggestions,
        total_suggestions=len(suggestions),
        summary=summary,
        preservation_guarantee=PRESERVATION_STATEMENT,
    )
