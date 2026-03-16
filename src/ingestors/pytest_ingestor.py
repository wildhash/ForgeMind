"""pytest failure ingestor.

Parses pytest output (text or JUnit XML) and converts failures
into structured CodeMemory objects.

Named pytest_ingestor.py to avoid name collision with the pytest package.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from xml.etree import ElementTree

from src.ingestors.base import BaseIngestor
from src.schemas.memory import BugCategory, CodeMemory, Severity

logger = logging.getLogger(__name__)

# Match pytest failure header: FAILED tests/test_foo.py::TestClass::test_method
_FAILED_RE = re.compile(r"FAILED\s+([\w/.\-]+::[\w:]+)")
# Match error lines in tracebacks
_ERROR_RE = re.compile(r"(E\s+.+)")


class PytestIngestor(BaseIngestor):
    """Parse pytest output (plain text or JUnit XML) into CodeMemory objects."""

    def source_name(self) -> str:
        """Return source identifier."""
        return "pytest"

    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Parse pytest output.

        Accepts:
        - Plain text pytest output (stdout)
        - Path to a JUnit XML file (.xml)
        - Path to a plain text file
        """
        if isinstance(raw_input, Path):
            if raw_input.suffix.lower() == ".xml":
                return self._parse_junit_xml(raw_input.read_text(encoding="utf-8"))
            return self._parse_text(raw_input.read_text(encoding="utf-8"))

        if isinstance(raw_input, str):
            stripped = raw_input.strip()
            if stripped.startswith("<"):
                return self._parse_junit_xml(stripped)
            return self._parse_text(stripped)

        return []

    def _parse_text(self, text: str) -> list[CodeMemory]:
        """Parse plain pytest text output."""
        memories: list[CodeMemory] = []
        lines = text.splitlines()

        # Collect failure blocks
        current_test: str | None = None
        current_block: list[str] = []

        for line in lines:
            m = _FAILED_RE.search(line)
            if m:
                if current_test and current_block:
                    memories.append(
                        self._build_memory(current_test, "\n".join(current_block))
                    )
                current_test = m.group(1)
                current_block = []
            elif current_test:
                current_block.append(line)

        # Flush last block
        if current_test and current_block:
            memories.append(self._build_memory(current_test, "\n".join(current_block)))

        logger.info("pytest ingestor produced %d memories from text", len(memories))
        return memories

    def _parse_junit_xml(self, xml_text: str) -> list[CodeMemory]:
        """Parse JUnit XML report."""
        memories: list[CodeMemory] = []
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            logger.error("Invalid JUnit XML: %s", exc)
            return []

        for testcase in root.iter("testcase"):
            failure = testcase.find("failure")
            if failure is None:
                failure = testcase.find("error")
            if failure is None:
                continue
            name = testcase.get("name", "unknown")
            classname = testcase.get("classname", "")
            message = failure.get("message", "") or (failure.text or "")
            full_name = f"{classname}::{name}" if classname else name
            memories.append(self._build_memory(full_name, message))

        logger.info("pytest ingestor produced %d memories from XML", len(memories))
        return memories

    def _build_memory(self, test_id: str, error_text: str) -> CodeMemory:
        """Build a CodeMemory from a test failure."""
        # Extract the error lines for a concise root cause
        error_lines = [ln.strip() for ln in error_text.splitlines() if ln.strip().startswith("E ")]
        root_cause = error_lines[0][2:].strip() if error_lines else error_text[:200]

        narrative = (
            f"pytest failure in {test_id}: {root_cause}. "
            f"Full output: {error_text[:600]}"
        )

        return CodeMemory(
            source="pytest",
            memory_type="failure",
            narrative=narrative,
            file_path=test_id.split("::")[0] if "::" in test_id else None,
            category=BugCategory.LOGIC_ERROR,
            severity=Severity.HIGH,
            tags=["pytest", "test-failure"],
            root_cause=root_cause,
            stack_trace=error_text[:1000] if hasattr(CodeMemory, "stack_trace") else None,
            lessons=[f"Test {test_id} failed: {root_cause}"],
        )
