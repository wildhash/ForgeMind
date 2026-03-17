"""Generation schemas for ForgeMind.

Defines the request/response shapes for the code generation pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.memory import CodeMemory


class CodeRequest(BaseModel):
    """What the user wants ForgeMind to generate."""

    task: str
    language: str = "python"
    context: str | None = None
    file_path: str | None = None
    test_requirements: str | None = None


class MemoryContext(BaseModel):
    """Assembled memory context injected into the generation prompt."""

    relevant_bugs: list[CodeMemory] = Field(default_factory=list)
    relevant_patterns: list[CodeMemory] = Field(default_factory=list)
    relevant_reviews: list[CodeMemory] = Field(default_factory=list)
    relevant_failures: list[CodeMemory] = Field(default_factory=list)
    active_strategies: list[str] = Field(default_factory=list)
    memory_summary: str = ""


class CodeResult(BaseModel):
    """Output of a generation cycle."""

    code: str
    reasoning: str
    memory_references: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    warnings: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Output of the verification pipeline."""

    passed: bool
    lint_errors: list[str] = Field(default_factory=list)
    type_errors: list[str] = Field(default_factory=list)
    test_results: dict[str, bool] = Field(default_factory=dict)
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
