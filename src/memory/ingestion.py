"""Memory ingestion pipeline.

Transforms raw CodeMemory objects into EverMemOS storage calls.
Provides a thin orchestration layer so callers don't need to
interact with the client directly.
"""

from __future__ import annotations

import logging
from typing import Any

from src.memory.client import EverMemOSClient
from src.schemas.memory import CodeMemory

logger = logging.getLogger(__name__)


async def ingest_memory(
    memory: CodeMemory,
    client: EverMemOSClient,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Store a single CodeMemory in EverMemOS.

    Args:
        memory: The structured memory to store.
        client: An open EverMemOSClient context.
        space_id: Override the default space routing.
    """
    result = await client.store_memory(memory, space_id=space_id)
    logger.info(
        "Ingested memory %s (type=%s, source=%s)",
        memory.id,
        memory.memory_type,
        memory.source,
    )
    return result


async def ingest_batch(
    memories: list[CodeMemory],
    client: EverMemOSClient,
    space_id: str | None = None,
) -> list[dict[str, Any]]:
    """Store a batch of CodeMemory objects, returning per-item results.

    Errors on individual items are caught and logged so a single bad
    memory does not abort the whole batch.
    """
    results: list[dict[str, Any]] = []
    for memory in memories:
        try:
            result = await ingest_memory(memory, client, space_id=space_id)
            results.append(result)
        except Exception as exc:
            logger.error("Failed to ingest memory %s: %s", memory.id, exc)
            results.append({"error": str(exc), "memory_id": memory.id})
    return results
