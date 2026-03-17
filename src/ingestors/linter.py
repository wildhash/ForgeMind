"""Linter output ingestor.

Parses output from ruff, ESLint, mypy, pylint, and similar linters
into structured CodeMemory objects.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from src.ingestors.base import BaseIngestor
from src.schemas.memory import BugCategory, CodeMemory, Severity

logger = logging.getLogger(__name__)

# ruff/pylint/mypy text line pattern: path:line:col: [code] message
_LINE_RE = re.compile(
    r"(?P<path>[^\s:]+):(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?P<code>[A-Z][A-Z0-9]+)?\s*(?P<msg>.+)"
)


def _severity_from_linter(tool: str, code: str) -> Severity:
    """Infer severity from linter tool and error code."""
    code_upper = code.upper()
    if tool in ("mypy", "pyright"):
        return Severity.HIGH
    if code_upper.startswith("E"):
        return Severity.MEDIUM
    if code_upper.startswith("W"):
        return Severity.LOW
    return Severity.INFO


def _category_from_code(code: str) -> BugCategory:
    """Map a linter error code to a BugCategory."""
    code_upper = code.upper()
    if code_upper.startswith("F8"):  # F811 redefinition, F841 unused
        return BugCategory.LOGIC_ERROR
    if code_upper in ("E711", "E712"):  # comparison to None/True
        return BugCategory.NULL_REFERENCE
    if code_upper.startswith("S"):  # bandit security
        return BugCategory.SECURITY_VULNERABILITY
    return BugCategory.OTHER


class LinterIngestor(BaseIngestor):
    """Parse linter output (ruff, ESLint, mypy, pylint) into CodeMemory."""

    def __init__(self, tool: str = "ruff") -> None:
        """Initialise with the linter tool name."""
        self._tool = tool.lower()

    def source_name(self) -> str:
        """Return source identifier."""
        return self._tool

    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Parse linter output text or JSON.

        Accepts plain text output (most linters) or JSON (ESLint --format=json).
        """
        content = await self._read_input(raw_input)
        if isinstance(content, dict):
            return self._parse_json([content])
        if isinstance(content, str):
            # Try JSON first
            stripped = content.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                try:
                    data = json.loads(stripped)
                    if isinstance(data, list):
                        return self._parse_json(data)
                    return self._parse_json([data])
                except json.JSONDecodeError:
                    pass
            # Fall back to line-by-line text parsing
            return self._parse_text(content)
        return []

    def _parse_text(self, text: str) -> list[CodeMemory]:
        """Parse line-by-line linter text output."""
        memories: list[CodeMemory] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = _LINE_RE.match(line)
            if not match:
                continue
            path = match.group("path")
            lineno = int(match.group("line"))
            code = match.group("code") or "LINT"
            msg = match.group("msg").strip()

            narrative = (
                f"{self._tool} linting error in {path}:{lineno} — "
                f"[{code}] {msg}"
            )
            memories.append(
                CodeMemory(
                    source=self._tool,
                    memory_type="bug",
                    narrative=narrative,
                    file_path=path,
                    category=_category_from_code(code),
                    severity=_severity_from_linter(self._tool, code),
                    tags=[self._tool, code, "lint"],
                    root_cause=f"[{code}] {msg}",
                    lessons=[narrative[:200]],
                )
            )
        logger.info("%s ingestor produced %d memories", self._tool, len(memories))
        return memories

    def _parse_json(self, data: list[dict]) -> list[CodeMemory]:
        """Parse ESLint-style JSON output."""
        memories: list[CodeMemory] = []
        for file_result in data:
            path = file_result.get("filePath") or file_result.get("file") or "unknown"
            messages = file_result.get("messages", [])
            for msg in messages:
                rule_id = msg.get("ruleId") or msg.get("code") or "LINT"
                message = msg.get("message") or msg.get("msg") or ""
                line = msg.get("line") or 0
                severity_num = msg.get("severity", 1)
                severity = Severity.HIGH if severity_num >= 2 else Severity.MEDIUM

                narrative = (
                    f"{self._tool} linting error in {path}:{line} — "
                    f"[{rule_id}] {message}"
                )
                memories.append(
                    CodeMemory(
                        source=self._tool,
                        memory_type="bug",
                        narrative=narrative,
                        file_path=path,
                        severity=severity,
                        tags=[self._tool, str(rule_id), "lint"],
                        root_cause=f"[{rule_id}] {message}",
                        lessons=[narrative[:200]],
                    )
                )
        logger.info("%s JSON ingestor produced %d memories", self._tool, len(memories))
        return memories
