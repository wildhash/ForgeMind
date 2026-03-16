"""Tests for the evolution tracking system."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.gardener.evolution import EvolutionTracker
from src.gardener.ranker import impact_score, rank_memories, recency_score, relevance_score
from src.gardener.report import generate_markdown_report, generate_text_report
from src.schemas.evolution import AgentState, ImprovementTrend
from src.schemas.memory import CodeMemory, Severity


class TestEvolutionTracker:
    def test_initial_state(self) -> None:
        tracker = EvolutionTracker()
        state = tracker.get_current_state()
        assert state.total_generations == 0
        assert state.generation_success_rate == 0.0
        assert state.evolution_score == 0.0

    def test_record_success(self) -> None:
        tracker = EvolutionTracker()
        tracker.record_generation(
            success=True, confidence=0.9, verification_score=1.0, language="python"
        )
        state = tracker.get_current_state()
        assert state.total_generations == 1
        assert state.successful_generations == 1
        assert state.generation_success_rate == 1.0

    def test_record_failure(self) -> None:
        tracker = EvolutionTracker()
        tracker.record_generation(
            success=False, confidence=0.3, verification_score=0.2, language="python"
        )
        state = tracker.get_current_state()
        assert state.total_generations == 1
        assert state.successful_generations == 0
        assert state.generation_success_rate == 0.0

    def test_mixed_generations(self) -> None:
        tracker = EvolutionTracker()
        for _ in range(8):
            tracker.record_generation(
                success=True, confidence=0.8, verification_score=0.9, language="python"
            )
        for _ in range(2):
            tracker.record_generation(
                success=False, confidence=0.3, verification_score=0.2, language="python"
            )
        state = tracker.get_current_state()
        assert state.total_generations == 10
        assert state.generation_success_rate == pytest.approx(0.8)

    def test_trend_insufficient_data(self) -> None:
        tracker = EvolutionTracker()
        tracker.record_generation(
            success=True, confidence=0.9, verification_score=1.0, language="python"
        )
        state = tracker.get_current_state()
        assert state.trend == ImprovementTrend.INSUFFICIENT_DATA

    def test_trend_improving(self) -> None:
        tracker = EvolutionTracker()
        for _ in range(10):
            tracker.record_generation(
                success=True, confidence=0.9, verification_score=1.0, language="python"
            )
        state = tracker.get_current_state()
        assert state.trend == ImprovementTrend.IMPROVING

    def test_trend_degrading(self) -> None:
        tracker = EvolutionTracker()
        for _ in range(10):
            tracker.record_generation(
                success=False, confidence=0.1, verification_score=0.0, language="python"
            )
        state = tracker.get_current_state()
        assert state.trend == ImprovementTrend.DEGRADING


class TestRanker:
    def test_recency_score_recent(self) -> None:
        now = datetime.now(UTC)
        recent = now - timedelta(days=1)
        score = recency_score(recent, now)
        assert score > 0.99

    def test_recency_score_old(self) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(days=365)
        score = recency_score(old, now)
        assert score < 0.1

    def test_relevance_score_perfect_match(self) -> None:
        m = CodeMemory(
            source="t", memory_type="bug", narrative="n", tags=["python", "async"]
        )
        score = relevance_score(m, ["python", "async"])
        assert score == pytest.approx(1.0)

    def test_relevance_score_no_overlap(self) -> None:
        m = CodeMemory(
            source="t", memory_type="bug", narrative="n", tags=["java"]
        )
        score = relevance_score(m, ["python"])
        assert score == 0.0

    def test_impact_score_critical(self) -> None:
        m = CodeMemory(
            source="t", memory_type="bug", narrative="n", severity=Severity.CRITICAL,
            lessons=["a", "b", "c"],
        )
        score = impact_score(m)
        assert score > 0.8

    def test_rank_memories_order(self, sample_memories: list[CodeMemory]) -> None:
        ranked = rank_memories(sample_memories, query_tags=["jwt", "auth"])
        # The memory with jwt/auth tags should rank higher
        assert ranked[0].tags and any(t in ("jwt", "auth") for t in ranked[0].tags)


class TestReports:
    def test_text_report_contains_key_fields(self) -> None:
        state = AgentState(
            total_generations=10,
            successful_generations=8,
            generation_success_rate=0.8,
            evolution_score=0.8,
            trend=ImprovementTrend.IMPROVING,
        )
        report = generate_text_report(state)
        assert "80.0%" in report
        assert "improving" in report.lower()
        assert "ForgeMind Evolution Report" in report

    def test_markdown_report_contains_table(self) -> None:
        state = AgentState(
            total_generations=5,
            successful_generations=5,
            generation_success_rate=1.0,
            evolution_score=1.0,
            trend=ImprovementTrend.IMPROVING,
        )
        report = generate_markdown_report(state)
        assert "# ForgeMind Evolution Report" in report
        assert "|" in report  # has table
        assert "100.0%" in report
