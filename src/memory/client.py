"""EverMemOS Cloud API async client.

Provides a high-level wrapper around the EverMemOS REST API with
connection pooling, exponential-backoff retries, and pagination support.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.schemas.memory import CodeMemory

logger = logging.getLogger(__name__)

MEMORY_SPACES = [
    "forgemind-bugs",
    "forgemind-reviews",
    "forgemind-patterns",
    "forgemind-failures",
    "forgemind-strategies",
    "forgemind-evolution",
]

# Map memory_type → default space
SPACE_BY_TYPE: dict[str, str] = {
    "bug": "forgemind-bugs",
    "review": "forgemind-reviews",
    "pattern": "forgemind-patterns",
    "failure": "forgemind-failures",
    "strategy": "forgemind-strategies",
    "evolution": "forgemind-evolution",
}


class EverMemOSClient:
    """Async wrapper around the EverMemOS Cloud REST API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Initialise the client, reading from settings if not provided."""
        settings = get_settings()
        self._base_url = (api_url or settings.evermemos_api_url).rstrip("/")
        self._api_key = api_key or settings.evermemos_api_key
        self._user_id = user_id or settings.evermemos_user_id
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> EverMemOSClient:
        """Open the underlying HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _client_or_raise(self) -> httpx.AsyncClient:
        """Return the active client, or raise if not entered."""
        if self._client is None:
            raise RuntimeError("Use 'async with EverMemOSClient() as client:'")
        return self._client

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def store_memory(
        self,
        memory: CodeMemory,
        space_id: str | None = None,
    ) -> dict[str, Any]:
        """Store a CodeMemory in EverMemOS.

        The narrative field becomes the message content; structured
        metadata is appended as natural text for richer search context.
        """
        client = self._client_or_raise()
        resolved_space = space_id or SPACE_BY_TYPE.get(memory.memory_type, "forgemind-bugs")

        # Build enriched content from narrative + key structured fields
        content_parts = [memory.narrative]
        if memory.root_cause:
            content_parts.append(f"Root cause: {memory.root_cause}")
        if memory.fix_pattern:
            content_parts.append(f"Fix pattern: {memory.fix_pattern}")
        if memory.lessons:
            content_parts.append("Lessons: " + "; ".join(memory.lessons))
        if memory.tags:
            content_parts.append("Tags: " + ", ".join(memory.tags))
        if memory.category:
            content_parts.append(f"Bug category: {memory.category.value}")
        content_parts.append(f"Severity: {memory.severity.value}")
        if memory.language:
            content_parts.append(f"Language: {memory.language}")

        payload = {
            "messages": [{"role": "user", "content": "\n".join(content_parts)}],
            "user_id": f"forgemind-{self._user_id}",
            "metadata": {
                "space_id": resolved_space,
                "memory_id": memory.id,
                "source": memory.source,
                "memory_type": memory.memory_type,
            },
        }

        response = await client.post("/memories/messages", json=payload)
        response.raise_for_status()
        logger.info("Stored memory %s in space %s", memory.id, resolved_space)
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def search_memories(
        self,
        query: str,
        space_id: str | None = None,
        retrieve_method: str = "hybrid",
        top_k: int = 10,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search memories using the specified retrieval method.

        Args:
            query: Natural language search query.
            space_id: Restrict search to a specific memory space.
            retrieve_method: One of keyword | vector | hybrid | lightweight | agentic.
            top_k: Number of results to return.
            page: Page number for pagination.
        """
        client = self._client_or_raise()
        params: dict[str, Any] = {
            "query": query,
            "user_id": f"forgemind-{self._user_id}",
            "retrieve_method": retrieve_method,
            "top_k": top_k,
            "page": page,
        }
        if space_id:
            params["space_id"] = space_id

        response = await client.get("/memories/search", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("memories", data) if isinstance(data, dict) else data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_profile(self) -> dict[str, Any]:
        """Retrieve the user/agent memory profile."""
        client = self._client_or_raise()
        response = await client.get(
            "/memories/profile",
            params={"user_id": f"forgemind-{self._user_id}"},
        )
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def delete_memory(self, memory_id: str) -> bool:
        """Remove a specific memory by ID."""
        client = self._client_or_raise()
        response = await client.delete(f"/memories/{memory_id}")
        if response.status_code == 404:
            logger.warning("Memory %s not found for deletion", memory_id)
            return False
        response.raise_for_status()
        return True

    async def health_check(self) -> bool:
        """Return True if the EverMemOS API is reachable."""
        try:
            client = self._client_or_raise()
            response = await client.get("/health")
            return response.status_code < 400
        except Exception:
            return False

    async def search_all_spaces(
        self,
        query: str,
        retrieve_method: str = "hybrid",
        top_k: int = 10,
    ) -> dict[str, list[dict[str, Any]]]:
        """Query all six memory spaces and return results keyed by space ID."""
        results: dict[str, list[dict[str, Any]]] = {}
        for space in MEMORY_SPACES:
            try:
                hits = await self.search_memories(
                    query=query,
                    space_id=space,
                    retrieve_method=retrieve_method,
                    top_k=top_k,
                )
                results[space] = hits
            except Exception as exc:
                logger.warning("Search failed for space %s: %s", space, exc)
                results[space] = []
        return results
