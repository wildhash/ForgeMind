"""Tests for ingestor parsing logic."""

from __future__ import annotations

import json

from src.ingestors.coderabbit import CodeRabbitIngestor
from src.ingestors.git_history import GitHistoryIngestor
from src.ingestors.linter import LinterIngestor
from src.ingestors.pytest_ingestor import PytestIngestor
from src.schemas.memory import Severity


class TestCodeRabbitIngestor:
    ingestor = CodeRabbitIngestor()

    async def test_parse_json_array(self) -> None:
        data = json.dumps([
            {
                "body": "Missing None check on Optional return",
                "path": "src/auth.py",
                "severity": "error",
                "suggestion": "Add `if result is None: raise ValueError(...)`",
            }
        ])
        memories = await self.ingestor.ingest(data)
        assert len(memories) == 1
        m = memories[0]
        assert m.source == "coderabbit"
        assert m.memory_type == "review"
        assert "None check" in m.narrative
        assert m.file_path == "src/auth.py"
        assert m.severity == Severity.HIGH

    async def test_parse_nested_json(self) -> None:
        data = {
            "comments": [
                {"body": "Use walrus operator", "severity": "suggestion"},
                {"body": "Add type hints", "severity": "info"},
            ]
        }
        memories = await self.ingestor.ingest(data)
        assert len(memories) == 2

    async def test_empty_body_skipped(self) -> None:
        data = json.dumps([{"body": "", "severity": "error"}])
        memories = await self.ingestor.ingest(data)
        assert len(memories) == 0

    async def test_invalid_json_returns_empty(self) -> None:
        memories = await self.ingestor.ingest("not valid json }{")
        assert memories == []

    def test_source_name(self) -> None:
        assert self.ingestor.source_name() == "coderabbit"


class TestLinterIngestor:
    async def test_parse_ruff_text(self) -> None:
        ruff_output = (
            "src/auth.py:42:5: E711 comparison to None (== None)\n"
            "src/utils.py:10:1: F841 local variable 'x' is assigned but never used\n"
        )
        ingestor = LinterIngestor(tool="ruff")
        memories = await ingestor.ingest(ruff_output)
        assert len(memories) == 2
        assert "E711" in memories[0].narrative
        assert memories[0].file_path == "src/auth.py"

    async def test_parse_eslint_json(self) -> None:
        eslint_json = json.dumps([
            {
                "filePath": "src/app.js",
                "messages": [
                    {"ruleId": "no-unused-vars", "message": "'x' is defined but never used", "line": 5, "severity": 2},
                ],
            }
        ])
        ingestor = LinterIngestor(tool="eslint")
        memories = await ingestor.ingest(eslint_json)
        assert len(memories) == 1
        assert "no-unused-vars" in memories[0].narrative
        assert memories[0].severity == Severity.HIGH

    async def test_empty_output(self) -> None:
        ingestor = LinterIngestor()
        memories = await ingestor.ingest("")
        assert memories == []

    def test_source_name(self) -> None:
        ingestor = LinterIngestor(tool="mypy")
        assert ingestor.source_name() == "mypy"


class TestPytestIngestor:
    ingestor = PytestIngestor()

    async def test_parse_text_failure(self) -> None:
        output = (
            "FAILED tests/test_auth.py::TestAuth::test_login\n"
            "E   AssertionError: expected True, got False\n"
            "E   assert result == True\n"
            "FAILED tests/test_api.py::test_get_user\n"
            "E   KeyError: 'user_id'\n"
        )
        memories = await self.ingestor.ingest(output)
        assert len(memories) == 2
        assert "AssertionError" in memories[0].narrative
        assert "KeyError" in memories[1].narrative

    async def test_parse_junit_xml(self) -> None:
        xml = """<?xml version="1.0" ?>
<testsuites>
  <testsuite name="tests">
    <testcase name="test_foo" classname="tests.test_bar">
      <failure message="AssertionError: 1 != 2">
        def test_foo():
            assert 1 == 2
        E   assert 1 == 2
      </failure>
    </testcase>
  </testsuite>
</testsuites>"""
        memories = await self.ingestor.ingest(xml)
        assert len(memories) == 1
        assert "AssertionError" in memories[0].narrative

    async def test_no_failures_returns_empty(self) -> None:
        output = "1 passed in 0.5s\n"
        memories = await self.ingestor.ingest(output)
        assert memories == []

    def test_source_name(self) -> None:
        assert self.ingestor.source_name() == "pytest"


class TestGitHistoryIngestor:
    ingestor = GitHistoryIngestor()

    async def test_parse_log_text_bug_fix(self) -> None:
        log = """commit abc1234
Author: Alice <alice@example.com>
Date: Mon Jan 1 2026

    fix: resolve null pointer in auth handler

commit def5678
Author: Bob <bob@example.com>
Date: Sun Dec 31 2025

    Add new feature for user profiles
"""
        memories = await self.ingestor.ingest(log)
        # Only the "fix" commit should produce a memory
        assert len(memories) >= 1
        assert any("null pointer" in m.narrative or "fix" in m.narrative.lower() for m in memories)

    async def test_non_bugfix_commit_ignored(self) -> None:
        log = "commit xyz9999\n\n    chore: update dependencies\n"
        memories = await self.ingestor.ingest(log)
        assert len(memories) == 0

    def test_source_name(self) -> None:
        assert self.ingestor.source_name() == "git"
