"""Core memory schemas for ForgeMind.

Every piece of code intelligence that enters EverMemOS is wrapped
in one of these structures.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class BugCategory(StrEnum):
    """Taxonomy of bug types for pattern matching across the memory."""

    NULL_REFERENCE = "null_reference"
    OFF_BY_ONE = "off_by_one"
    TYPE_MISMATCH = "type_mismatch"
    RACE_CONDITION = "race_condition"
    RESOURCE_LEAK = "resource_leak"
    API_MISUSE = "api_misuse"
    STATE_MANAGEMENT = "state_management"
    BOUNDARY_VIOLATION = "boundary_violation"
    SECURITY_VULNERABILITY = "security_vulnerability"
    PERFORMANCE_REGRESSION = "performance_regression"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    LOGIC_ERROR = "logic_error"
    CONCURRENCY_BUG = "concurrency_bug"
    ENCODING_ERROR = "encoding_error"
    OTHER = "other"


class Severity(StrEnum):
    """Severity levels for code memories."""

    CRITICAL = "critical"  # crashes, data loss, security holes
    HIGH = "high"  # wrong output, broken features
    MEDIUM = "medium"  # degraded behavior, edge cases
    LOW = "low"  # cosmetic, style, minor inefficiency
    INFO = "info"  # suggestions, improvements


class CodeMemory(BaseModel):
    """The atomic memory unit.

    Every piece of code intelligence that enters EverMemOS is wrapped
    in this structure. The ``narrative`` field is the primary field for
    semantic search — write it as a senior dev explaining the bug to a
    colleague.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str  # "coderabbit" | "github" | "pytest" | "ruff" | etc.
    memory_type: str  # "bug" | "review" | "pattern" | "failure" | "strategy"

    # Primary field for EverMemOS semantic search
    narrative: str

    # Structured metadata
    language: str = "python"
    file_path: str | None = None
    category: BugCategory | None = None
    severity: Severity = Severity.MEDIUM
    tags: list[str] = Field(default_factory=list)

    # Code snapshots
    code_before: str | None = None
    code_after: str | None = None
    diff: str | None = None

    # Distilled lessons
    lessons: list[str] = Field(default_factory=list)
    root_cause: str | None = None
    fix_pattern: str | None = None

    # Linking
    related_memories: list[str] = Field(default_factory=list)
    source_url: str | None = None


class ReviewFeedback(BaseModel):
    """Wraps code review feedback from CodeRabbit, Copilot, or similar tools."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str  # "coderabbit" | "copilot" | "manual"
    reviewer: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    suggestion: str
    reason: str
    severity: Severity = Severity.MEDIUM
    accepted: bool | None = None  # None = unknown
    tags: list[str] = Field(default_factory=list)

    def to_code_memory(self) -> CodeMemory:
        """Convert to a CodeMemory for storage in EverMemOS."""
        narrative = (
            f"Code review feedback from {self.source}"
            + (f" by {self.reviewer}" if self.reviewer else "")
            + (f" on {self.file_path}" if self.file_path else "")
            + f": {self.suggestion}. Reason: {self.reason}."
            + (f" Accepted: {self.accepted}." if self.accepted is not None else "")
        )
        return CodeMemory(
            id=self.id,
            timestamp=self.timestamp,
            source=self.source,
            memory_type="review",
            narrative=narrative,
            file_path=self.file_path,
            severity=self.severity,
            tags=self.tags,
            lessons=[self.suggestion],
        )


class FailureEvent(BaseModel):
    """Wraps CI/CD and runtime failures."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str  # "github_actions" | "pytest" | "ruff" | etc.
    failure_type: str  # "build" | "test" | "lint" | "runtime"
    error_message: str
    stack_trace: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    file_path: str | None = None
    category: BugCategory | None = None
    severity: Severity = Severity.HIGH
    tags: list[str] = Field(default_factory=list)
    source_url: str | None = None

    def to_code_memory(self) -> CodeMemory:
        """Convert to a CodeMemory for storage in EverMemOS."""
        narrative = (
            f"CI/CD failure ({self.failure_type}) from {self.source}: "
            f"{self.error_message}."
        )
        if self.stack_trace:
            narrative += f" Stack trace excerpt: {self.stack_trace[:500]}"
        return CodeMemory(
            id=self.id,
            timestamp=self.timestamp,
            source=self.source,
            memory_type="failure",
            narrative=narrative,
            file_path=self.file_path,
            category=self.category,
            severity=self.severity,
            tags=self.tags,
            source_url=self.source_url,
        )
