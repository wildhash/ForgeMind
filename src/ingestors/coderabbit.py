"""CodeRabbit review ingestor.

Parses CodeRabbit JSON review output and converts it to CodeMemory objects.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.ingestors.base import BaseIngestor
from src.schemas.memory import CodeMemory, Severity

logger = logging.getLogger(__name__)

_SEVERITY_MAP: dict[str, Severity] = {
    "error": Severity.HIGH,
    "warning": Severity.MEDIUM,
    "info": Severity.INFO,
    "suggestion": Severity.LOW,
    "nitpick": Severity.LOW,
}


def _map_severity(raw: str) -> Severity:
    """Map a CodeRabbit severity string to a Severity enum."""
    return _SEVERITY_MAP.get(raw.lower(), Severity.MEDIUM)


class CodeRabbitIngestor(BaseIngestor):
    """Ingest CodeRabbit review JSON output into CodeMemory objects."""

    def source_name(self) -> str:
        """Return source identifier."""
        return "coderabbit"

    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Parse CodeRabbit review output.

        Accepts a JSON string, a parsed dict, or a Path to a JSON file.
        Supports both flat comment arrays and nested review structures.
        """
        data = await self._read_input(raw_input)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as exc:
                logger.error("CodeRabbit input is not valid JSON: %s", exc)
                return []

        memories: list[CodeMemory] = []

        # Handle an array of comments directly
        if isinstance(data, list):
            comments = data
        else:
            # Nested structure: {"reviews": [...], "comments": [...]}
            comments = data.get("comments", data.get("reviews", []))

        for item in comments:
            memories.extend(self._parse_comment(item))

        logger.info("CodeRabbit ingestor produced %d memories", len(memories))
        return memories

    def _parse_comment(self, item: dict) -> list[CodeMemory]:
        """Convert a single CodeRabbit comment dict to CodeMemory."""
        body: str = item.get("body") or item.get("content") or item.get("message", "")
        if not body.strip():
            return []

        path: str | None = item.get("path") or item.get("file")
        severity_raw: str = item.get("severity") or item.get("type") or "info"
        severity = _map_severity(severity_raw)
        suggestion: str = item.get("suggestion") or item.get("fix") or ""
        line: int | None = item.get("line") or item.get("line_number")

        narrative = "CodeRabbit review"
        if path:
            narrative += f" on {path}"
            if line:
                narrative += f":{line}"
        narrative += f": {body[:800]}"
        if suggestion:
            narrative += f" Suggested fix: {suggestion[:400]}"

        lessons: list[str] = []
        if body:
            lessons.append(body[:200])
        if suggestion:
            lessons.append(f"Fix: {suggestion[:200]}")

        return [
            CodeMemory(
                source="coderabbit",
                memory_type="review",
                narrative=narrative,
                file_path=path,
                severity=severity,
                tags=["coderabbit", severity_raw.lower()],
                lessons=lessons,
                fix_pattern=suggestion[:200] if suggestion else None,
            )
        ]
