"""Copilot suggestions ingestor.

Ingests GitHub Copilot suggestion acceptance/rejection telemetry.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.ingestors.base import BaseIngestor
from src.schemas.memory import CodeMemory, Severity

logger = logging.getLogger(__name__)


class CopilotIngestor(BaseIngestor):
    """Ingest Copilot suggestion patterns into CodeMemory objects."""

    def source_name(self) -> str:
        """Return source identifier."""
        return "copilot"

    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Parse Copilot telemetry input.

        Accepts a JSON string, dict, or Path with a list of suggestion events.
        Each event should have at least: suggestion (str), accepted (bool).
        """
        data = await self._read_input(raw_input)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as exc:
                logger.error("Copilot input is not valid JSON: %s", exc)
                return []

        if isinstance(data, dict):
            events = data.get("suggestions", data.get("events", [data]))
        else:
            events = data

        memories: list[CodeMemory] = []
        for event in events:
            memory = self._parse_event(event)
            if memory:
                memories.append(memory)

        logger.info("Copilot ingestor produced %d memories", len(memories))
        return memories

    def _parse_event(self, event: dict) -> CodeMemory | None:
        """Convert a single Copilot suggestion event to CodeMemory."""
        suggestion: str = event.get("suggestion") or event.get("text") or ""
        if not suggestion.strip():
            return None

        accepted: bool | None = event.get("accepted")
        file_path: str | None = event.get("file") or event.get("path")
        language: str = event.get("language") or "unknown"

        action = "accepted" if accepted else ("rejected" if accepted is False else "shown")
        narrative = (
            f"Copilot suggestion {action}"
            + (f" in {file_path}" if file_path else "")
            + f": {suggestion[:600]}"
        )

        memory_type = "pattern" if accepted else "review"
        return CodeMemory(
            source="copilot",
            memory_type=memory_type,
            narrative=narrative,
            file_path=file_path,
            language=language,
            severity=Severity.INFO,
            tags=["copilot", action, language],
            lessons=[narrative[:200]],
        )
