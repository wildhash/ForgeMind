"""Evolution tracker — measures and records the agent's improvement over time."""

from __future__ import annotations

import logging

from src.memory.client import EverMemOSClient
from src.memory.ingestion import ingest_memory
from src.schemas.evolution import AgentState, EvolutionEntry, ImprovementTrend
from src.schemas.memory import CodeMemory, Severity

logger = logging.getLogger(__name__)


class EvolutionTracker:
    """Track and record the agent's evolution over time."""

    def __init__(self) -> None:
        """Initialise the tracker with an empty history."""
        self._snapshots: list[AgentState] = []

    def record_generation(
        self,
        *,
        success: bool,
        confidence: float,
        verification_score: float,
        language: str,
    ) -> None:
        """Record a single generation outcome."""
        if not self._snapshots:
            self._snapshots.append(AgentState())

        state = self._snapshots[-1]
        state.total_generations += 1
        if success:
            state.successful_generations += 1

        state.generation_success_rate = (
            state.successful_generations / state.total_generations
        )
        state.trend = self._compute_trend()
        state.evolution_score = self._compute_evolution_score()

    def _compute_trend(self) -> ImprovementTrend:
        """Compute the current improvement trend from recent snapshots."""
        if len(self._snapshots) < 1:
            return ImprovementTrend.INSUFFICIENT_DATA
        current = self._snapshots[-1]
        if current.total_generations < 5:
            return ImprovementTrend.INSUFFICIENT_DATA
        rate = current.generation_success_rate
        if rate >= 0.8:
            return ImprovementTrend.IMPROVING
        if rate >= 0.5:
            return ImprovementTrend.STABLE
        return ImprovementTrend.DEGRADING

    def _compute_evolution_score(self) -> float:
        """Compute a 0-1 evolution score from the current state."""
        if not self._snapshots:
            return 0.0
        state = self._snapshots[-1]
        if state.total_generations == 0:
            return 0.0
        return round(state.generation_success_rate, 3)

    def get_current_state(self) -> AgentState:
        """Return the most recent AgentState snapshot."""
        if not self._snapshots:
            return AgentState()
        return self._snapshots[-1]

    async def record_and_store(
        self,
        *,
        success: bool,
        confidence: float,
        verification_score: float,
        language: str,
        client: EverMemOSClient,
    ) -> EvolutionEntry:
        """Record a generation outcome and persist it to EverMemOS."""
        self.record_generation(
            success=success,
            confidence=confidence,
            verification_score=verification_score,
            language=language,
        )
        state = self.get_current_state()
        entry = EvolutionEntry(
            event_type="generation_success" if success else "generation_failure",
            description=(
                f"Generation {'succeeded' if success else 'failed'} "
                f"(language={language}, confidence={confidence:.2f}, "
                f"score={verification_score:.2f}). "
                f"Overall success rate: {state.generation_success_rate:.2f} "
                f"across {state.total_generations} generations."
            ),
            metrics={
                "confidence": confidence,
                "verification_score": verification_score,
                "success_rate": state.generation_success_rate,
                "evolution_score": state.evolution_score,
            },
            tags=[language, "generation_success" if success else "generation_failure"],
        )

        memory = CodeMemory(
            source="forgemind-evolution",
            memory_type="evolution",
            narrative=entry.description,
            severity=Severity.INFO,
            tags=entry.tags,
            lessons=[entry.description[:200]],
        )
        await ingest_memory(memory, client, space_id="forgemind-evolution")
        logger.info("Evolution entry stored: %s", entry.event_type)
        return entry
