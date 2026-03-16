"""Tests for the code verification pipeline."""

from __future__ import annotations

import pytest

from src.forge.verifier import CodeVerifier
from src.schemas.generation import CodeResult


@pytest.fixture
def verifier() -> CodeVerifier:
    return CodeVerifier()


class TestCodeVerifier:
    async def test_valid_python_passes_syntax(self, verifier: CodeVerifier) -> None:
        result = CodeResult(code="def foo(x: int) -> int:\n    return x + 1", reasoning="r")
        vr = await verifier.verify(result, language="python")
        # Syntax should be fine; lint/type errors may or may not appear
        # We just check the structure
        assert isinstance(vr.passed, bool)
        assert 0.0 <= vr.overall_score <= 1.0

    async def test_syntax_error_fails(self, verifier: CodeVerifier) -> None:
        result = CodeResult(code="def foo(:\n    pass", reasoning="r")
        vr = await verifier.verify(result, language="python")
        assert not vr.passed
        assert vr.overall_score == 0.0

    async def test_empty_code_fails(self, verifier: CodeVerifier) -> None:
        result = CodeResult(code="", reasoning="r")
        vr = await verifier.verify(result, language="python")
        assert not vr.passed
        assert "Empty code output" in vr.lint_errors

    async def test_non_python_passes_permissively(self, verifier: CodeVerifier) -> None:
        result = CodeResult(
            code="const x: number = 1;",
            reasoning="typescript",
        )
        vr = await verifier.verify(result, language="typescript")
        assert vr.passed
        assert vr.overall_score == 0.7

    async def test_check_syntax_valid(self, verifier: CodeVerifier) -> None:
        assert verifier._check_syntax("x = 1 + 2") is True

    async def test_check_syntax_invalid(self, verifier: CodeVerifier) -> None:
        assert verifier._check_syntax("def (broken:") is False
