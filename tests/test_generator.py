"""Tests for the code generation pipeline."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.forge.generator import CodeGenerator, _parse_code_result
from src.schemas.generation import CodeRequest, MemoryContext


class TestParseCodeResult:
    def test_valid_json(self) -> None:
        raw = json.dumps({
            "code": "def foo(): pass",
            "reasoning": "Simple function",
            "confidence": 0.9,
            "warnings": [],
            "memory_references": ["mem-001"],
        })
        result = _parse_code_result(raw)
        assert result.code == "def foo(): pass"
        assert result.confidence == 0.9
        assert result.memory_references == ["mem-001"]

    def test_json_with_markdown_fences(self) -> None:
        raw = "```json\n" + json.dumps({"code": "x = 1", "reasoning": "r", "confidence": 0.5}) + "\n```"
        result = _parse_code_result(raw)
        assert result.code == "x = 1"

    def test_non_json_fallback(self) -> None:
        raw = "def hello():\n    print('world')"
        result = _parse_code_result(raw)
        assert "def hello" in result.code
        assert result.confidence == 0.3
        assert len(result.warnings) > 0

    def test_empty_json_object(self) -> None:
        raw = json.dumps({})
        result = _parse_code_result(raw)
        assert result.code == ""
        assert result.confidence == 0.5


class TestCodeGenerator:
    @pytest.fixture
    def mock_memory_context(self) -> MemoryContext:
        return MemoryContext(
            memory_summary="No relevant prior memories.",
            active_strategies=["Always add type hints"],
        )

    @patch("src.forge.generator.assemble_context")
    @patch("src.forge.generator.anthropic.Anthropic")
    async def test_generate_basic(
        self,
        mock_anthropic_cls: MagicMock,
        mock_assemble: AsyncMock,
        mock_memory_context: MemoryContext,
        mock_settings: None,
    ) -> None:
        """generate() should call recall, build prompt, call Claude, parse result."""
        mock_assemble.return_value = mock_memory_context

        # Mock Anthropic client
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=json.dumps({
            "code": "def add(a: int, b: int) -> int:\n    return a + b",
            "reasoning": "Simple addition function",
            "confidence": 0.95,
            "warnings": [],
            "memory_references": [],
        }))]
        mock_anthropic_cls.return_value.messages.create.return_value = mock_msg

        generator = CodeGenerator()
        request = CodeRequest(task="Write an add function", language="python")
        result = await generator.generate(request, memory_client=None)

        assert "def add" in result.code
        assert result.confidence == 0.95

    @patch("src.forge.generator.assemble_context")
    @patch("src.forge.generator.anthropic.Anthropic")
    async def test_generate_without_memory_client(
        self,
        mock_anthropic_cls: MagicMock,
        mock_assemble: AsyncMock,
        mock_settings: None,
    ) -> None:
        """generate() should work with memory_client=None (uses empty context)."""
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=json.dumps({
            "code": "x = 1",
            "reasoning": "simple",
            "confidence": 0.7,
            "warnings": [],
        }))]
        mock_anthropic_cls.return_value.messages.create.return_value = mock_msg

        generator = CodeGenerator()
        request = CodeRequest(task="Set x to 1")
        result = await generator.generate(request)

        assert result.code == "x = 1"
        # assemble_context should NOT have been called (no client)
        mock_assemble.assert_not_called()
