"""Generic LLM-powered ingestor.

Accepts raw text from ANY tool (CharlieHelps, BugBot, Macroscope,
InfinitiCode, etc.) and uses Claude to extract structured CodeMemory fields.
This is the killer feature â€” no custom parser needed for new tools.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import anthropic

from src.config import get_settings
from src.ingestors.base import BaseIngestor
from src.schemas.memory import BugCategory, CodeMemory, Severity

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = """\
You are a code intelligence extractor for ForgeMind. Given raw output from any
developer tool, extract structured information about bugs, reviews, failures,
or patterns. Return ONLY valid JSON â€” no prose, no markdown fences.

Return a JSON array of objects, each with these keys:
- narrative (string, required): Rich description of what happened, why, and the fix/lesson.
  Write as if explaining to a senior developer. Include root cause, fix, and pattern.
- memory_type (string): "bug" | "review" | "pattern" | "failure" | "strategy"
- category (string): one of null_reference | off_by_one | type_mismatch | race_condition |
  resource_leak | api_misuse | state_management | boundary_violation |
  security_vulnerability | performance_regression | configuration_error |
  dependency_conflict | logic_error | concurrency_bug | encoding_error | other
- severity (string): critical | high | medium | low | info
- root_cause (string | null): one-line root cause
- fix_pattern (string | null): reusable fix pattern
- lessons (array of strings): 1-3 sentence takeaways
- tags (array of strings): freeform tags
- file_path (string | null): relative file path if mentioned
- language (string): programming language, default "python"

If the input contains multiple separate issues, return one object per issue.
Return [] if no actionable code intelligence is found.
"""


class GenericIngestor(BaseIngestor):
    """LLM-powered ingestor for any raw tool output."""

    def __init__(self, source: str = "generic") -> None:
        """Initialise with an optional source label."""
        self._source = source

    def source_name(self) -> str:
        """Return source identifier."""
        return self._source

    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Parse raw tool output via LLM extraction.

        Args:
            raw_input: Any raw text, dict payload, or Path to a text file.
        """
        import asyncio

        content = await self._read_input(raw_input)
        if isinstance(content, dict):
            content = json.dumps(content, indent=2)

        if not content or not content.strip():
            return []

        settings = get_settings()
        if not settings.anthropic_api_key:
            logger.warning("No Anthropic API key â€” generic ingestor unavailable")
            return []

        try:
            def _extract_via_llm() -> str:
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                message = client.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=2048,
                    system=_EXTRACTION_SYSTEM,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Extract code intelligence from this tool output:\n\n{content[:8000]}",
                        }
                    ],
                )
                return message.content[0].text.strip()

            raw_json = await asyncio.to_thread(_extract_via_llm)
        except Exception as exc:
            logger.error("LLM extraction failed: %s", exc)
            return []

        # Strip any accidental markdown fences
        if raw_json.startswith("```"):
            raw_json = re.sub(r"^```[a-z]*\n?", "", raw_json, flags=re.MULTILINE)
            raw_json = raw_json.rstrip("`").strip()

        try:
            items = json.loads(raw_json)
            if not isinstance(items, list):
                items = [items]
        except json.JSONDecodeError as exc:
            logger.error("LLM returned invalid JSON: %s\nRaw: %s", exc, raw_json[:500])
            return []

        memories: list[CodeMemory] = []
        for item in items:
            memory = self._build_memory(item)
            if memory:
                memories.append(memory)

        logger.info(
            "Generic ingestor (%s) produced %d memories", self._source, len(memories)
        )
        return memories

    def _build_memory(self, item: dict) -> CodeMemory | None:
        """Convert an extracted item dict to a CodeMemory."""
        narrative = item.get("narrative", "").strip()
        if not narrative:
            return None

        # Parse category
        category: BugCategory | None = None
        cat_raw = item.get("category")
        if cat_raw:
            try:
                category = BugCategory(cat_raw)
            except ValueError:
                category = BugCategory.OTHER

        # Parse severity
        sev_raw = item.get("severity", "medium")
        try:
            severity = Severity(sev_raw)
        except ValueError:
            severity = Severity.MEDIUM

        return CodeMemory(
            source=self._source,
            memory_type=item.get("memory_type", "bug"),
            narrative=narrative,
            category=category,
            severity=severity,
            root_cause=item.get("root_cause"),
            fix_pattern=item.get("fix_pattern"),
            lessons=item.get("lessons") or [],
            tags=item.get("tags") or [self._source],
            file_path=item.get("file_path"),
            language=item.get("language") or "python",
        )

