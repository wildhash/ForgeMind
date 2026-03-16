"""Meta-strategist — analyses memory landscape and derives actionable strategies."""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

import anthropic

from src.config import get_settings
from src.forge.prompts import STRATEGY_SYSTEM
from src.memory.client import EverMemOSClient
from src.memory.ingestion import ingest_memory
from src.schemas.evolution import StrategyProfile
from src.schemas.memory import CodeMemory, Severity

logger = logging.getLogger(__name__)


class Strategist:
    """Analyse the memory landscape to derive and store meta-strategies."""

    async def run(self, client: EverMemOSClient) -> list[StrategyProfile]:
        """Perform a full strategy analysis cycle.

        1. Query all memory spaces for recent memories.
        2. Identify top bug categories.
        3. Generate new strategies via LLM.
        4. Store strategies in forgemind-strategies.
        5. Return the derived StrategyProfile list.
        """
        memories = await self._gather_memories(client)
        if not memories:
            logger.info("No memories found for strategy analysis")
            return []

        # Count bug categories
        category_counts: Counter[str] = Counter()
        for m in memories:
            if m.category:
                category_counts[m.category.value] += 1

        top_categories = [cat for cat, _ in category_counts.most_common(5)]

        # Generate strategies via LLM
        strategies = await self._generate_strategies(memories, top_categories)

        # Store each strategy as a memory
        for strategy in strategies:
            memory = CodeMemory(
                source="forgemind-strategist",
                memory_type="strategy",
                narrative=(
                    f"Strategy: {strategy.name}. {strategy.description} "
                    f"Applies to: {', '.join(strategy.applies_to)}. "
                    f"Evidence: {strategy.evidence_count} memories. "
                    f"Confidence: {strategy.confidence:.2f}."
                ),
                severity=Severity.INFO,
                tags=["strategy"] + strategy.applies_to,
                lessons=[strategy.description],
            )
            await ingest_memory(memory, client, space_id="forgemind-strategies")

        logger.info("Strategist derived %d strategies", len(strategies))
        return strategies

    async def _gather_memories(
        self, client: EverMemOSClient
    ) -> list[CodeMemory]:
        """Gather recent memories from bugs and failures spaces."""
        from src.memory.recall import _hit_to_code_memory

        memories: list[CodeMemory] = []
        for space in ("forgemind-bugs", "forgemind-failures", "forgemind-reviews"):
            try:
                hits = await client.search_memories(
                    query="bug failure error",
                    space_id=space,
                    retrieve_method="vector",
                    top_k=30,
                )
                for h in hits:
                    m = _hit_to_code_memory(h)
                    if m:
                        memories.append(m)
            except Exception as exc:
                logger.warning("Could not gather memories from %s: %s", space, exc)
        return memories

    async def _generate_strategies(
        self,
        memories: list[CodeMemory],
        top_categories: list[str],
    ) -> list[StrategyProfile]:
        """Use LLM to derive strategies from memory analysis."""
        settings = get_settings()
        if not settings.anthropic_api_key:
            return []

        snippets = [m.narrative[:300] for m in memories[:20]]
        user_content = (
            f"Top bug categories: {', '.join(top_categories)}.\n\n"
            f"Sample memories:\n" + "\n---\n".join(snippets)
        )

        try:
            llm = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            message = llm.messages.create(
                model=settings.anthropic_model,
                max_tokens=2048,
                system=STRATEGY_SYSTEM,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = message.content[0].text.strip()
            data: dict[str, Any] = json.loads(raw)
            raw_strategies: list[dict] = data.get("strategies", [])
        except Exception as exc:
            logger.error("Strategy generation failed: %s", exc)
            return []

        profiles: list[StrategyProfile] = []
        for item in raw_strategies:
            try:
                profiles.append(
                    StrategyProfile(
                        name=item.get("name", "unnamed"),
                        description=item.get("description", ""),
                        applies_to=item.get("applies_to", []),
                        evidence_count=int(item.get("evidence_count", 0)),
                        confidence=float(item.get("confidence", 0.5)),
                    )
                )
            except Exception as exc:
                logger.debug("Skipping malformed strategy item: %s", exc)
        return profiles
