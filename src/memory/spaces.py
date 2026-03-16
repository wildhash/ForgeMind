"""Memory space management and initialisation for ForgeMind.

Ensures the six canonical memory spaces exist before the agent
attempts to read or write memories.
"""

from __future__ import annotations

import logging
from typing import Any

from src.memory.client import MEMORY_SPACES, EverMemOSClient

logger = logging.getLogger(__name__)


async def ensure_spaces(client: EverMemOSClient) -> dict[str, Any]:
    """Verify that all required memory spaces are reachable.

    EverMemOS creates spaces on first write, so this performs a lightweight
    health-check style search to validate connectivity per space.

    Returns a dict mapping space_id → {"ok": bool, "error": str | None}.
    """
    status: dict[str, Any] = {}
    for space in MEMORY_SPACES:
        try:
            await client.search_memories(
                query="ping",
                space_id=space,
                retrieve_method="keyword",
                top_k=1,
            )
            status[space] = {"ok": True, "error": None}
            logger.debug("Space %s is reachable", space)
        except Exception as exc:
            status[space] = {"ok": False, "error": str(exc)}
            logger.warning("Space %s not reachable: %s", space, exc)
    return status


def get_space_for_type(memory_type: str) -> str:
    """Return the canonical space ID for a given memory type."""
    from src.memory.client import SPACE_BY_TYPE

    return SPACE_BY_TYPE.get(memory_type, "forgemind-bugs")
