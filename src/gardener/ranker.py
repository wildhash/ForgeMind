"""Memory ranker — scores and ranks memories by relevance, recency, and impact."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from src.schemas.memory import CodeMemory, Severity

# Weight constants
_SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 2.0,
    Severity.HIGH: 1.5,
    Severity.MEDIUM: 1.0,
    Severity.LOW: 0.7,
    Severity.INFO: 0.5,
}

_RECENCY_HALF_LIFE_DAYS = 90.0  # memories lose half their recency score in 90 days


def recency_score(timestamp: datetime, now: datetime | None = None) -> float:
    """Compute a 0-1 recency score decaying exponentially with age.

    More recent memories score closer to 1.0.
    """
    if now is None:
        now = datetime.now(UTC)
    # Ensure both are timezone-aware
    ts = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp
    age_days = max(0.0, (now - ts).total_seconds() / 86400)
    return math.exp(-math.log(2) * age_days / _RECENCY_HALF_LIFE_DAYS)


def relevance_score(memory: CodeMemory, query_tags: list[str]) -> float:
    """Compute a 0-1 relevance score based on tag overlap."""
    if not query_tags:
        return 0.5
    memory_tags_lower = {t.lower() for t in memory.tags}
    query_tags_lower = {t.lower() for t in query_tags}
    overlap = len(memory_tags_lower & query_tags_lower)
    union = len(memory_tags_lower | query_tags_lower)
    return overlap / union if union else 0.0


def impact_score(memory: CodeMemory) -> float:
    """Compute a 0-1 impact score based on severity and lesson count."""
    sev = _SEVERITY_WEIGHTS.get(memory.severity, 1.0)
    lesson_bonus = min(len(memory.lessons) * 0.1, 0.3)
    return min(sev / 2.0 + lesson_bonus, 1.0)


def rank_memories(
    memories: list[CodeMemory],
    query_tags: list[str] | None = None,
    now: datetime | None = None,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> list[CodeMemory]:
    """Rank memories by a weighted combination of recency, impact, and relevance.

    Args:
        memories: List of CodeMemory objects to rank.
        query_tags: Tags from the current query for relevance scoring.
        now: Reference time (defaults to UTC now).
        weights: (recency_w, impact_w, relevance_w) — must sum to 1.

    Returns:
        Memories sorted descending by composite score.
    """
    tags = query_tags or []
    recency_w, impact_w, relevance_w = weights

    def score(m: CodeMemory) -> float:
        return (
            recency_w * recency_score(m.timestamp, now)
            + impact_w * impact_score(m)
            + relevance_w * relevance_score(m, tags)
        )

    return sorted(memories, key=score, reverse=True)
