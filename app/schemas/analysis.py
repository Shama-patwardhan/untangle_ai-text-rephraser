"""Schemas for writing analysis requests and responses."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Request schema for text analysis."""

    text: str = Field(
        ...,
        description="The plain text content to analyze.",
        examples=["This is a sample paragraph. It contains multiple sentences."],
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("text")
    @classmethod
    def validate_text_not_empty_or_whitespace(cls, value: str) -> str:
        """Reject empty or whitespace-only input."""
        if not value or not value.strip():
            raise ValueError("Input text cannot be empty or contain only whitespace.")
        return value


class TextSpan(BaseModel):
    """Character offset span identifying a text segment."""

    start: int = Field(description="0-indexed start character offset in original text.")
    end: int = Field(description="0-indexed end character offset in original text.")
    text: str = Field(description="Text content of the segment.")

    model_config = ConfigDict(extra="forbid")


class RepeatedItem(BaseModel):
    """Count of a repeated word."""

    item: str = Field(description="The repeated word.")
    count: int = Field(description="Total occurrence count.")

    model_config = ConfigDict(extra="forbid")


class RepeatedPhrase(BaseModel):
    """Count and occurrence spans of a repeated multiword phrase."""

    phrase: str = Field(description="The repeated multiword phrase.")
    count: int = Field(description="Total occurrence count.")
    spans: list[TextSpan] = Field(
        default_factory=list,
        description="Locations of occurrences in the text.",
    )

    model_config = ConfigDict(extra="forbid")


class TextStatistics(BaseModel):
    """Deterministic structural and lexical statistics of the analyzed text."""

    character_count: int = Field(
        description="Total character count including whitespace."
    )
    character_count_no_spaces: int = Field(
        description="Character count excluding whitespace characters."
    )
    word_count: int = Field(description="Total word count.")
    sentence_count: int = Field(description="Total sentence count.")
    paragraph_count: int = Field(description="Total paragraph count.")
    avg_sentence_length: float = Field(
        description="Average sentence length measured in words (arithmetic mean)."
    )
    sentence_length_std_dev: float = Field(
        description=(
            "Sample standard deviation of sentence lengths in words "
            "(Bessel's correction; 0.0 for <= 1 sentences)."
        )
    )
    sentence_lengths: list[int] = Field(
        description="Ordered sequence of word counts for each sentence."
    )
    sentence_length_distribution: dict[str, int] = Field(
        description="Counts of sentences binned by length ranges."
    )
    punctuation_frequencies: dict[str, int] = Field(
        description="Frequencies of individual punctuation marks."
    )
    repeated_words: list[RepeatedItem] = Field(
        description="Frequently occurring non-stopword tokens."
    )
    repeated_phrases: list[RepeatedPhrase] = Field(
        description="Identified repeated multiword phrases."
    )

    model_config = ConfigDict(extra="forbid")


class Finding(BaseModel):
    """Explainable finding describing an observed stylistic pattern."""

    rule_id: str = Field(
        description="Stable machine-readable identifier for the rule.",
        examples=["RULE_REPEATED_PHRASES"],
    )
    title: str = Field(
        description="Human-readable title of the observation.",
        examples=["Repeated multiword phrase"],
    )
    explanation: str = Field(
        description="Concise neutral explanation of the observed pattern."
    )
    severity: Literal["low", "medium", "high"] = Field(
        description="Strength or salience of the pattern observation.",
        examples=["medium"],
    )
    evidence: dict[str, Any] = Field(
        description="Observed empirical metrics and parameter thresholds."
    )
    span: TextSpan | None = Field(
        default=None,
        description="Relevant text span when reliably localizable.",
    )

    model_config = ConfigDict(extra="forbid")


class AnalyzeResponse(BaseModel):
    """Response schema for the text analysis endpoint."""

    analysis_id: str = Field(
        description="Unique identifier for this analysis run.",
        examples=["ana_01j7xyz..."],
    )
    statistics: TextStatistics = Field(
        description="Deterministic structural statistics."
    )
    findings: list[Finding] = Field(
        description="List of explainable stylistic pattern observations."
    )
    summary: str = Field(description="Neutral summary of the analysis findings.")
    disclaimer: str = Field(
        description="Standard disclaimer regarding the limits of stylistic analysis."
    )

    model_config = ConfigDict(extra="forbid")
