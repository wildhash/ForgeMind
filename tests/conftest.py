"""Shared pytest fixtures and mock helpers."""

from __future__ import annotations

from typing import Any

import pytest

from src.schemas.memory import BugCategory, CodeMemory, Severity


@pytest.fixture
def sample_code_memory() -> CodeMemory:
    """A minimal CodeMemory for use in tests."""
    return CodeMemory(
        id="test-memory-001",
        source="pytest",
        memory_type="bug",
        narrative=(
            "TypeError in authentication flow — JWT decode returns Optional[dict] "
            "but .get() was called without None guard. Fix: add explicit None check."
        ),
        language="python",
        file_path="src/auth.py",
        category=BugCategory.NULL_REFERENCE,
        severity=Severity.HIGH,
        tags=["jwt", "auth", "null-check"],
        lessons=["Always guard Optional returns from third-party libs"],
        root_cause="Missing None check on Optional[dict] return",
        fix_pattern="if result is None: raise ValueError('Expected dict, got None')",
    )


@pytest.fixture
def sample_memories(sample_code_memory: CodeMemory) -> list[CodeMemory]:
    """A small list of varied CodeMemory objects."""
    return [
        sample_code_memory,
        CodeMemory(
            id="test-memory-002",
            source="coderabbit",
            memory_type="review",
            narrative="Off-by-one error in pagination logic — use < instead of <=",
            language="python",
            category=BugCategory.OFF_BY_ONE,
            severity=Severity.MEDIUM,
            tags=["pagination", "loop"],
        ),
        CodeMemory(
            id="test-memory-003",
            source="github",
            memory_type="pattern",
            narrative="Using contextlib.asynccontextmanager for DB sessions works well",
            language="python",
            severity=Severity.INFO,
            tags=["database", "async", "pattern"],
        ),
    ]


@pytest.fixture
def mock_evermemos_search_response() -> list[dict[str, Any]]:
    """Fake EverMemOS search response."""
    return [
        {
            "id": "mem-001",
            "content": "JWT TypeError: missing None guard on Optional return",
            "metadata": {
                "source": "pytest",
                "memory_type": "bug",
                "severity": "high",
                "space_id": "forgemind-bugs",
            },
        },
        {
            "id": "mem-002",
            "content": "Off-by-one in loop boundary",
            "metadata": {
                "source": "coderabbit",
                "memory_type": "review",
                "severity": "medium",
                "space_id": "forgemind-reviews",
            },
        },
    ]


@pytest.fixture
def mock_evermemos_store_response() -> dict[str, Any]:
    """Fake EverMemOS store response."""
    return {"id": "stored-memory-abc123", "status": "ok"}


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch settings to avoid needing real API keys in tests."""
    monkeypatch.setenv("EVERMEMOS_API_KEY", "test-key")
    monkeypatch.setenv("EVERMEMOS_USER_ID", "test-user")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("EVERMEMOS_API_URL", "https://api.evermind.ai/v1")
