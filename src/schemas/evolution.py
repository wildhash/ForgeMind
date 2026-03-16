"""Evolution schemas for ForgeMind.

Tracks the agent's learning over time.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ImprovementTrend(StrEnum):
    """Direction of improvement for a given metric."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


class EvolutionEntry(BaseModel):
    """A single timestamped entry in the agent's evolution log.

    Captures what the agent learned, when, and from what event.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str  # "generation_success" | "generation_failure" | "strategy_update" | etc.
    description: str
    source_memory_ids: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class StrategyProfile(BaseModel):
    """A meta-strategy derived from memory analysis.

    Strategies are actionable rules the agent applies during generation
    based on patterns observed across many memories.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    name: str
    description: str
    applies_to: list[str] = Field(default_factory=list)  # languages / domains
    evidence_count: int = 0
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    active: bool = True
    tags: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Snapshot of the agent's current knowledge state."""

    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_memories: int = 0
    memories_by_space: dict[str, int] = Field(default_factory=dict)
    generation_success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    total_generations: int = 0
    successful_generations: int = 0
    evolution_score: float = Field(ge=0.0, le=1.0, default=0.0)
    top_bug_categories: list[str] = Field(default_factory=list)
    active_strategies: list[str] = Field(default_factory=list)
    trend: ImprovementTrend = ImprovementTrend.INSUFFICIENT_DATA
