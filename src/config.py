"""Pydantic Settings for ForgeMind configuration.

Reads from .env file and environment variables.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # EverMemOS
    evermemos_api_url: str = Field(
        default="https://api.evermind.ai/v1",
        description="EverMemOS Cloud API base URL",
    )
    evermemos_api_key: str = Field(
        default="",
        description="EverMemOS Cloud API key",
    )
    evermemos_user_id: str = Field(
        default="forgemind-default",
        description="User ID for memory space isolation",
    )

    # Anthropic
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic Claude API key",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use for generation",
    )

    # GitHub (optional)
    github_token: str = Field(
        default="",
        description="GitHub personal access token (optional)",
    )

    # ForgeMind
    forgemind_log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG | INFO | WARNING | ERROR",
    )
    forgemind_memory_language: str = Field(
        default="en",
        description="Primary language for memory narratives",
    )
    forgemind_max_retries: int = Field(
        default=3,
        description="Max generation retries on verification failure",
    )
    forgemind_top_k_memories: int = Field(
        default=10,
        description="Number of memories to retrieve per query",
    )


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
