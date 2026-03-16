"""Tests for schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.evolution import AgentState, EvolutionEntry, ImprovementTrend, StrategyProfile
from src.schemas.generation import CodeRequest, CodeResult, VerificationResult
from src.schemas.memory import BugCategory, CodeMemory, FailureEvent, ReviewFeedback, Severity


class TestCodeMemory:
    def test_default_fields_populated(self) -> None:
        m = CodeMemory(source="test", memory_type="bug", narrative="A test narrative")
        assert m.id  # UUID auto-generated
        assert m.timestamp
        assert m.severity == Severity.MEDIUM
        assert m.tags == []
        assert m.lessons == []

    def test_all_fields_accepted(self, sample_code_memory: CodeMemory) -> None:
        assert sample_code_memory.id == "test-memory-001"
        assert sample_code_memory.category == BugCategory.NULL_REFERENCE
        assert sample_code_memory.severity == Severity.HIGH
        assert "jwt" in sample_code_memory.tags

    def test_severity_enum_values(self) -> None:
        for s in ("critical", "high", "medium", "low", "info"):
            m = CodeMemory(source="t", memory_type="bug", narrative="n", severity=s)
            assert m.severity.value == s

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValidationError):
            CodeMemory(source="t", memory_type="bug", narrative="n", severity="extreme")

    def test_bug_category_enum(self) -> None:
        m = CodeMemory(
            source="t",
            memory_type="bug",
            narrative="n",
            category=BugCategory.RACE_CONDITION,
        )
        assert m.category == BugCategory.RACE_CONDITION


class TestReviewFeedback:
    def test_to_code_memory_basic(self) -> None:
        rf = ReviewFeedback(
            source="coderabbit",
            suggestion="Add None check",
            reason="Function returns Optional",
        )
        cm = rf.to_code_memory()
        assert cm.memory_type == "review"
        assert cm.source == "coderabbit"
        assert "Add None check" in cm.narrative

    def test_to_code_memory_with_reviewer(self) -> None:
        rf = ReviewFeedback(
            source="copilot",
            reviewer="alice",
            suggestion="Use walrus operator",
            reason="Cleaner code",
            accepted=True,
        )
        cm = rf.to_code_memory()
        assert "alice" in cm.narrative
        assert "Accepted: True" in cm.narrative


class TestFailureEvent:
    def test_to_code_memory_basic(self) -> None:
        fe = FailureEvent(
            source="github_actions",
            failure_type="test",
            error_message="AssertionError: expected 42 got 43",
        )
        cm = fe.to_code_memory()
        assert cm.memory_type == "failure"
        assert "AssertionError" in cm.narrative

    def test_stack_trace_truncated(self) -> None:
        long_trace = "Traceback:\n" + "  line\n" * 200
        fe = FailureEvent(
            source="ci",
            failure_type="runtime",
            error_message="Error",
            stack_trace=long_trace,
        )
        cm = fe.to_code_memory()
        assert len(cm.narrative) < 5000  # Not bloated


class TestCodeRequest:
    def test_defaults(self) -> None:
        r = CodeRequest(task="Write a function")
        assert r.language == "python"
        assert r.context is None

    def test_full(self) -> None:
        r = CodeRequest(
            task="Write an HTTP client",
            language="typescript",
            context="Use axios",
            file_path="src/client.ts",
            test_requirements="Must handle 404",
        )
        assert r.language == "typescript"


class TestCodeResult:
    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            CodeResult(code="x", reasoning="y", confidence=1.5)
        with pytest.raises(ValidationError):
            CodeResult(code="x", reasoning="y", confidence=-0.1)

    def test_valid(self) -> None:
        r = CodeResult(code="def foo(): pass", reasoning="simple", confidence=0.9)
        assert r.confidence == 0.9
        assert r.warnings == []


class TestVerificationResult:
    def test_passed(self) -> None:
        v = VerificationResult(passed=True, overall_score=1.0)
        assert v.passed
        assert v.lint_errors == []

    def test_failed_with_errors(self) -> None:
        v = VerificationResult(
            passed=False,
            lint_errors=["E501: line too long"],
            type_errors=["error: Incompatible types"],
            overall_score=0.3,
        )
        assert not v.passed
        assert len(v.lint_errors) == 1


class TestEvolutionSchemas:
    def test_agent_state_defaults(self) -> None:
        s = AgentState()
        assert s.total_generations == 0
        assert s.trend == ImprovementTrend.INSUFFICIENT_DATA
        assert s.evolution_score == 0.0

    def test_strategy_profile(self) -> None:
        sp = StrategyProfile(
            name="Async timeouts",
            description="Always include timeout params in async functions",
            applies_to=["python"],
            confidence=0.85,
            evidence_count=12,
        )
        assert sp.active
        assert sp.confidence == 0.85

    def test_evolution_entry(self) -> None:
        entry = EvolutionEntry(
            event_type="generation_success",
            description="Generated HTTP client successfully",
            metrics={"confidence": 0.9, "score": 1.0},
        )
        assert entry.event_type == "generation_success"
        assert entry.metrics["confidence"] == 0.9
