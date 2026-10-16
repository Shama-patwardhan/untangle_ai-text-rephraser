"""Application configuration module."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support and safe defaults."""

    app_name: str = Field(
        default="Untangle",
        description="The name of the application.",
    )
    app_version: str = Field(
        default="0.1.0",
        description="The semantic version of the application.",
    )
    environment: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        description="Application running environment.",
    )
    api_prefix: str = Field(
        default="/api/v1",
        description="Prefix for API routes.",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode.",
    )

    # Phase 2A: Text Analysis Settings
    max_text_length: int = Field(
        default=20000,
        ge=1,
        description="Maximum allowed input character length for analysis.",
    )
    min_repeated_phrase_words: int = Field(
        default=3,
        ge=2,
        description="Minimum word count for repeated multiword phrase detection.",
    )
    min_phrase_repetitions: int = Field(
        default=2,
        ge=2,
        description="Minimum repetitions required to flag a multiword phrase.",
    )
    uniform_sentence_min_count: int = Field(
        default=3,
        ge=2,
        description="Minimum sentence count for uniformity evaluation.",
    )
    uniform_sentence_std_dev_threshold: float = Field(
        default=1.5,
        ge=0.0,
        description="Std dev threshold (words) for sentence length uniformity.",
    )
    repetitive_transition_min_count: int = Field(
        default=2,
        ge=2,
        description="Minimum occurrences of repeated sentence transitions.",
    )
    frequent_punctuation_threshold: float = Field(
        default=0.5,
        ge=0.0,
        description="Ratio of punctuation marks per sentence to flag frequency.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Ensure api_prefix starts with a slash and does not end with one."""
        prefix = value.strip()
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        if prefix.endswith("/") and len(prefix) > 1:
            prefix = prefix.rstrip("/")
        return prefix


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
