"""Memory recall — the intelligence layer above raw search.

Takes a CodeRequest and assembles a MemoryContext by querying all
relevant memory spaces, deduplicating results, and generating a
concise briefing via the LLM.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from src.config import get_settings
from src.memory.client import EverMemOSClient
from src.schemas.generation import CodeRequest, MemoryContext
from src.schemas.memory import CodeMemory, Severity

logger = logging.getLogger(__name__)


def _hit_to_code_memory(hit: dict[str, Any]) -> CodeMemory | None:
    """Convert a raw EverMemOS search hit to a CodeMemory.

    EverMemOS returns varying shapes depending on the retrieve_method.
    We extract the textual content and wrap it in a minimal CodeMemory.
    """
    try:
        content: str = (
            hit.get("content")
            or hit.get("text")
            or hit.get("message", {}).get("content", "")
            or str(hit)
        )
        metadata: dict[str, Any] = hit.get("metadata", {})
        return CodeMemory(
            id=hit.get("id", metadata.get("memory_id", "")),
            source=metadata.get("source", "evermemos"),
            memory_type=metadata.get("memory_type", "bug"),
            narrative=content,
            severity=Severity(metadata.get("severity", "medium")),
        )
    except Exception as exc:
        logger.debug("Could not parse hit to CodeMemory: %s — %s", hit, exc)
        return None


def _deduplicate(memories: list[CodeMemory]) -> list[CodeMemory]:
    """Remove duplicate memories by ID, preserving insertion order."""
    seen: set[str] = set()
    unique: list[CodeMemory] = []
    for m in memories:
        if m.id not in seen:
            seen.add(m.id)
            unique.append(m)
    return unique


async def _generate_memory_summary(
    memories_by_space: dict[str, list[CodeMemory]],
    task: str,
    settings: Any,
) -> str:
    """Use the LLM to produce a concise briefing from retrieved memories."""
    if not any(memories_by_space.values()):
        return "No relevant prior memories found."

    snippets: list[str] = []
    for space, memories in memories_by_space.items():
        for m in memories[:3]:  # top 3 per space
            snippets.append(f"[{space}] {m.narrative[:300]}")

    prompt = (
        "You are ForgeMind's memory analyst. Summarise the following memories "
        "retrieved for the task below. Focus on actionable warnings and patterns. "
        "Be concise — 3-5 sentences max.\n\n"
        f"TASK: {task}\n\n"
        "RETRIEVED MEMORIES:\n" + "\n\n".join(snippets)
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as exc:
        logger.warning("Could not generate memory summary: %s", exc)
        return "Memory summary unavailable."


async def assemble_context(
    request: CodeRequest,
    client: EverMemOSClient,
) -> MemoryContext:
    """Assemble a MemoryContext for a CodeRequest.

    Queries all relevant memory spaces using appropriate retrieval methods,
    deduplicates, ranks, and builds a LLM-generated summary briefing.
    """
    settings = get_settings()
    top_k = settings.forgemind_top_k_memories

    # Build a rich query from the request
    query = request.task
    if request.context:
        query = f"{query} Context: {request.context}"
    if request.language:
        query = f"{query} Language: {request.language}"

    # Query each space with the appropriate method
    bugs_hits = await client.search_memories(
        query=query,
        space_id="forgemind-bugs",
        retrieve_method="agentic",
        top_k=top_k,
    )
    patterns_hits = await client.search_memories(
        query=query,
        space_id="forgemind-patterns",
        retrieve_method="hybrid",
        top_k=top_k,
    )
    reviews_hits = await client.search_memories(
        query=query,
        space_id="forgemind-reviews",
        retrieve_method="hybrid",
        top_k=top_k,
    )
    failures_hits = await client.search_memories(
        query=query,
        space_id="forgemind-failures",
        retrieve_method="hybrid",
        top_k=top_k,
    )
    strategies_hits = await client.search_memories(
        query=query,
        space_id="forgemind-strategies",
        retrieve_method="keyword",
        top_k=top_k,
    )

    # Parse hits into CodeMemory objects
    bugs = _deduplicate([m for h in bugs_hits if (m := _hit_to_code_memory(h))])
    patterns = _deduplicate([m for h in patterns_hits if (m := _hit_to_code_memory(h))])
    reviews = _deduplicate([m for h in reviews_hits if (m := _hit_to_code_memory(h))])
    failures = _deduplicate([m for h in failures_hits if (m := _hit_to_code_memory(h))])
    strategies = [
        m.narrative
        for h in strategies_hits
        if (m := _hit_to_code_memory(h))
    ]

    memories_by_space: dict[str, list[CodeMemory]] = {
        "forgemind-bugs": bugs,
        "forgemind-patterns": patterns,
        "forgemind-reviews": reviews,
        "forgemind-failures": failures,
    }

    summary = await _generate_memory_summary(memories_by_space, request.task, settings)

    return MemoryContext(
        relevant_bugs=bugs[:5],
        relevant_patterns=patterns[:5],
        relevant_reviews=reviews[:5],
        relevant_failures=failures[:5],
        active_strategies=strategies[:5],
        memory_summary=summary,
    )
