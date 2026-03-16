"""Tests for the EverMemOS memory client."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from src.memory.client import SPACE_BY_TYPE, EverMemOSClient
from src.schemas.memory import CodeMemory


class TestEverMemOSClient:
    @pytest.fixture
    def client_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVERMEMOS_API_KEY", "test-key")
        monkeypatch.setenv("EVERMEMOS_USER_ID", "test-user")
        monkeypatch.setenv("EVERMEMOS_API_URL", "https://api.evermind.ai/v1")

    @respx.mock
    async def test_store_memory_success(
        self,
        client_settings: None,
        sample_code_memory: CodeMemory,
    ) -> None:
        """store_memory should POST to /memories/messages and return the response."""
        respx.post("https://api.evermind.ai/v1/memories/messages").mock(
            return_value=httpx.Response(200, json={"id": "abc", "status": "ok"})
        )
        async with EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        ) as client:
            result = await client.store_memory(sample_code_memory)
        assert result["status"] == "ok"

    @respx.mock
    async def test_search_memories_success(
        self,
        client_settings: None,
        mock_evermemos_search_response: list[dict[str, Any]],
    ) -> None:
        """search_memories should GET /memories/search and return hits."""
        respx.get("https://api.evermind.ai/v1/memories/search").mock(
            return_value=httpx.Response(
                200, json={"memories": mock_evermemos_search_response}
            )
        )
        async with EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        ) as client:
            hits = await client.search_memories(query="JWT auth bug")
        assert len(hits) == 2
        assert hits[0]["id"] == "mem-001"

    @respx.mock
    async def test_delete_memory_success(self, client_settings: None) -> None:
        """delete_memory should DELETE /memories/{id}."""
        respx.delete("https://api.evermind.ai/v1/memories/abc123").mock(
            return_value=httpx.Response(200, json={"deleted": True})
        )
        async with EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        ) as client:
            ok = await client.delete_memory("abc123")
        assert ok is True

    @respx.mock
    async def test_delete_memory_not_found(self, client_settings: None) -> None:
        """delete_memory should return False for 404 responses."""
        respx.delete("https://api.evermind.ai/v1/memories/missing").mock(
            return_value=httpx.Response(404, json={"error": "not found"})
        )
        async with EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        ) as client:
            ok = await client.delete_memory("missing")
        assert ok is False

    @respx.mock
    async def test_health_check_ok(self, client_settings: None) -> None:
        """health_check should return True when API responds < 400."""
        respx.get("https://api.evermind.ai/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        async with EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        ) as client:
            healthy = await client.health_check()
        assert healthy is True

    @respx.mock
    async def test_health_check_failure(self, client_settings: None) -> None:
        """health_check should return False when API is unreachable."""
        respx.get("https://api.evermind.ai/v1/health").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        async with EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        ) as client:
            healthy = await client.health_check()
        assert healthy is False

    def test_space_by_type_mapping(self) -> None:
        """SPACE_BY_TYPE should map all expected memory types."""
        assert SPACE_BY_TYPE["bug"] == "forgemind-bugs"
        assert SPACE_BY_TYPE["review"] == "forgemind-reviews"
        assert SPACE_BY_TYPE["pattern"] == "forgemind-patterns"
        assert SPACE_BY_TYPE["failure"] == "forgemind-failures"
        assert SPACE_BY_TYPE["strategy"] == "forgemind-strategies"
        assert SPACE_BY_TYPE["evolution"] == "forgemind-evolution"

    def test_client_requires_context_manager(
        self, client_settings: None
    ) -> None:
        """Calling store_memory outside a context manager should raise RuntimeError."""
        client = EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        )
        with pytest.raises(RuntimeError, match="async with"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                client.store_memory(
                    CodeMemory(source="t", memory_type="bug", narrative="n")
                )
            )

    @respx.mock
    async def test_store_memory_routes_to_correct_space(
        self,
        client_settings: None,
    ) -> None:
        """store_memory should include the correct space_id in metadata."""
        captured_body: dict = {}

        def capture(request: httpx.Request) -> httpx.Response:
            import json
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "x"})

        respx.post("https://api.evermind.ai/v1/memories/messages").mock(
            side_effect=capture
        )
        memory = CodeMemory(source="t", memory_type="review", narrative="n")
        async with EverMemOSClient(
            api_url="https://api.evermind.ai/v1",
            api_key="test-key",
            user_id="test-user",
        ) as client:
            await client.store_memory(memory)

        assert captured_body["metadata"]["space_id"] == "forgemind-reviews"
