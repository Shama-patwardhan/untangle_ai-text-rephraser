"""Schemas for text improvement and controlled reconstruction."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.analysis import TextSpan


class PreservationCheck(BaseModel):
    """Factual and semantic preservation verification results."""

    status: Literal["verified", "warnings_detected", "manual_review_required"] = Field(
        default="verified",
        description="Preservation status based on automated checks.",
        examples=["verified"],
    )
    numbers_preserved: bool = Field(
        description="Whether all numbers, percentages, and amounts were preserved."
    )
    citations_preserved: bool = Field(
        description="Whether all citations and reference tags were preserved."
    )
    entities_preserved: bool = Field(
        description="Whether all capitalized proper nouns/entities were preserved."
    )
    certainty_preserved: bool = Field(
        description="Whether polarity and modality/certainty levels were preserved."
    )
    details: list[str] = Field(
        default_factory=list,
        description="Detailed verification observations or notes.",
    )

    model_config = ConfigDict(extra="forbid")


class ImprovementSuggestion(BaseModel):
    """Reviewable suggestion to improve an identified writing pattern."""

    suggestion_id: str = Field(
        description="Unique identifier for this suggestion.",
        examples=["sug_01j7xyz"],
    )
    rule_id: str = Field(
        description="Rule or finding identifier that triggered the suggestion.",
        examples=["RULE_REDUNDANT_PHRASING"],
    )
    category: Literal["redundancy", "repetition", "structure", "transition"] = Field(
        description="Category of the writing improvement opportunity.",
        examples=["redundancy"],
    )
    title: str = Field(
        description="Human-readable title of the suggested improvement.",
        examples=["Replace wordy phrase with concise alternative"],
    )
    original_text: str = Field(
        description="Original text segment or phrase being improved.",
    )
    suggested_text: str = Field(
        description="Recommended alternative phrasing.",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="Alternative phrasing choices available for user review.",
    )
    span: TextSpan = Field(
        description="0-indexed character offsets of the original text in the input.",
    )
    explanation: str = Field(
        description="Clear rationale explaining how the suggestion improves the text.",
    )
    preservation: PreservationCheck = Field(
        description="Verification that meaning, facts, and citations are preserved.",
    )

    model_config = ConfigDict(extra="forbid")


class ImproveRequest(BaseModel):
    """Request schema for text improvement suggestions."""

    text: str = Field(
        ...,
        description="The plain text content to analyze and improve.",
        examples=["In order to achieve optimal performance, we must make a decision."],
    )
    include_draft_preview: bool = Field(
        default=True,
        description=(
            "Whether to include a non-destructive draft preview with suggested "
            "improvements applied for side-by-side comparison."
        ),
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("text")
    @classmethod
    def validate_text_not_empty_or_whitespace(cls, value: str) -> str:
        """Reject empty or whitespace-only input."""
        if not value or not value.strip():
            raise ValueError("Input text cannot be empty or contain only whitespace.")
        return value


class ImproveResponse(BaseModel):
    """Response schema containing reviewable improvement suggestions."""

    improvement_id: str = Field(
        description="Unique identifier for this improvement session.",
        examples=["imp_01j7xyz..."],
    )
    original_text: str = Field(
        description="Original input text submitted for improvement.",
    )
    suggested_draft: str | None = Field(
        default=None,
        description=(
            "Non-destructive preview draft incorporating suggested improvements. "
            "Provided for review only; never silently replaces the original text."
        ),
    )
    suggestions: list[ImprovementSuggestion] = Field(
        description=(
            "List of reviewable suggestions with alternatives and preservation checks."
        ),
    )
    total_suggestions: int = Field(
        description="Total number of improvement opportunities identified.",
    )
    summary: str = Field(
        description="Neutral summary of identified improvement opportunities.",
    )
    preservation_guarantee: str = Field(
        description="Explicit guarantee regarding fact and meaning preservation.",
    )

    model_config = ConfigDict(extra="forbid")
