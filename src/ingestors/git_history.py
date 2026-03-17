"""Git history ingestor.

Analyses git log to find bug-fix commits, reverts, and patch patterns.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.ingestors.base import BaseIngestor
from src.schemas.memory import BugCategory, CodeMemory, Severity

logger = logging.getLogger(__name__)

# Patterns that indicate a bug-fix commit
_BUG_FIX_RE = re.compile(
    r"\b(fix|fixes|fixed|bug|bugfix|hotfix|patch|revert|regression|issue|closes?|resolves?)\b",
    re.IGNORECASE,
)


class GitHistoryIngestor(BaseIngestor):
    """Ingest bug-fix commits from git log output."""

    def source_name(self) -> str:
        """Return source identifier."""
        return "git"

    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Parse git log output.

        Accepts:
        - A Path to the repository root (uses gitpython)
        - A string of raw `git log --format=...` output
        - A dict with key "repo_path" pointing to the repository
        """
        if isinstance(raw_input, dict):
            repo_path = raw_input.get("repo_path")
            if repo_path:
                return await self._ingest_from_repo(Path(repo_path))
            return []

        if isinstance(raw_input, Path):
            if raw_input.is_dir():
                return await self._ingest_from_repo(raw_input)
            return self._parse_log_text(raw_input.read_text(encoding="utf-8"))

        if isinstance(raw_input, str):
            stripped = raw_input.strip()
            if Path(stripped).is_dir():
                return await self._ingest_from_repo(Path(stripped))
            return self._parse_log_text(stripped)

        return []

    async def _ingest_from_repo(self, repo_path: Path) -> list[CodeMemory]:
        """Use gitpython to walk the commit history."""
        try:
            import git  # gitpython

            repo = git.Repo(repo_path, search_parent_directories=True)
            memories: list[CodeMemory] = []
            for commit in repo.iter_commits(max_count=200):
                if _BUG_FIX_RE.search(commit.message):
                    diff_text = ""
                    try:
                        if commit.parents:
                            diff_text = repo.git.diff(
                                commit.parents[0].hexsha, commit.hexsha, "--stat"
                            )
                    except Exception:
                        pass
                    memories.append(
                        self._build_memory(
                            sha=commit.hexsha[:12],
                            message=commit.message.strip(),
                            author=str(commit.author),
                            diff=diff_text,
                        )
                    )
            logger.info("git ingestor produced %d memories from repo", len(memories))
            return memories
        except ImportError:
            logger.warning("gitpython not installed; falling back to text parsing")
            return []
        except Exception as exc:
            logger.error("git repo ingestion failed: %s", exc)
            return []

    def _parse_log_text(self, text: str) -> list[CodeMemory]:
        """Parse plain `git log` text output."""
        memories: list[CodeMemory] = []
        # Simple block split on "commit <sha>"
        blocks = re.split(r"^commit [0-9a-f]{7,40}", text, flags=re.MULTILINE)
        for block in blocks:
            if not block.strip():
                continue
            lines = block.strip().splitlines()
            message = " ".join(lines).strip()
            if _BUG_FIX_RE.search(message):
                memories.append(
                    self._build_memory(sha="unknown", message=message[:500])
                )
        logger.info("git ingestor produced %d memories from text", len(memories))
        return memories

    def _build_memory(
        self,
        sha: str,
        message: str,
        author: str = "",
        diff: str = "",
    ) -> CodeMemory:
        """Build a CodeMemory from a bug-fix commit."""
        narrative = f"Bug-fix commit {sha}"
        if author:
            narrative += f" by {author}"
        narrative += f": {message[:600]}"
        if diff:
            narrative += f". Changed files: {diff[:300]}"

        return CodeMemory(
            source="git",
            memory_type="bug",
            narrative=narrative,
            category=BugCategory.LOGIC_ERROR,
            severity=Severity.MEDIUM,
            tags=["git", "bug-fix"],
            root_cause=message[:200],
            lessons=[f"Commit message: {message[:200]}"],
            diff=diff[:1000] if diff else None,
        )
