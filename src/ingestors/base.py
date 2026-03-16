"""Abstract base ingestor interface.

All ingestors implement this interface, accepting raw tool output
and returning structured CodeMemory objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.schemas.memory import CodeMemory


class BaseIngestor(ABC):
    """Base class for all ForgeMind ingestors."""

    @abstractmethod
    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Parse raw input and return structured CodeMemory objects.

        Args:
            raw_input: Raw output from the source tool — may be a string,
                       a parsed dict, or a Path to a file.
        """
        ...

    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier (e.g., 'coderabbit', 'github')."""
        ...

    async def _read_input(self, raw_input: str | dict | Path) -> str | dict:
        """Normalise raw_input to string or dict, reading files as needed."""
        if isinstance(raw_input, Path):
            return raw_input.read_text(encoding="utf-8")
        return raw_input
