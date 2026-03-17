"""GitHub ingestor.

Ingests bugs, PR reviews, Actions failures, and bug-fix commits
from the GitHub REST API.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from src.config import get_settings
from src.ingestors.base import BaseIngestor
from src.schemas.memory import BugCategory, CodeMemory, Severity

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

# Heuristic mapping of issue labels → BugCategory
LABEL_TO_CATEGORY: dict[str, BugCategory] = {
    "bug": BugCategory.LOGIC_ERROR,
    "security": BugCategory.SECURITY_VULNERABILITY,
    "performance": BugCategory.PERFORMANCE_REGRESSION,
    "race-condition": BugCategory.RACE_CONDITION,
    "null-pointer": BugCategory.NULL_REFERENCE,
    "type-error": BugCategory.TYPE_MISMATCH,
    "off-by-one": BugCategory.OFF_BY_ONE,
    "config": BugCategory.CONFIGURATION_ERROR,
    "dependency": BugCategory.DEPENDENCY_CONFLICT,
    "encoding": BugCategory.ENCODING_ERROR,
}


def _infer_category(labels: list[str]) -> BugCategory:
    """Map GitHub issue labels to a BugCategory."""
    for label in labels:
        label_lower = label.lower()
        for key, category in LABEL_TO_CATEGORY.items():
            if key in label_lower:
                return category
    return BugCategory.OTHER


def _infer_severity(labels: list[str]) -> Severity:
    """Map GitHub priority labels to Severity."""
    for label in labels:
        label_lower = label.lower()
        if "critical" in label_lower or "blocker" in label_lower:
            return Severity.CRITICAL
        if "high" in label_lower or "major" in label_lower:
            return Severity.HIGH
        if "low" in label_lower or "minor" in label_lower:
            return Severity.LOW
    return Severity.MEDIUM


class GitHubIngestor(BaseIngestor):
    """Ingest bugs, PR reviews, Actions failures, and bug-fix commits from GitHub."""

    def __init__(self, token: str | None = None) -> None:
        """Initialise with a GitHub token (reads from settings if not provided)."""
        settings = get_settings()
        self._token = token or settings.github_token
        self._headers = {
            "Authorization": f"token {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def source_name(self) -> str:
        """Return source identifier."""
        return "github"

    async def ingest(self, raw_input: str | dict | Path) -> list[CodeMemory]:
        """Ingest from GitHub.

        raw_input should be a string in the form "owner/repo" or a dict
        with keys: repo (required), since (optional ISO date), limit (optional int).
        """
        if isinstance(raw_input, Path):
            raw_input = raw_input.read_text()
        if isinstance(raw_input, str):
            raw_input = {"repo": raw_input.strip()}

        repo: str = raw_input["repo"]
        since: str | None = raw_input.get("since")
        limit: int = int(raw_input.get("limit", 50))

        memories: list[CodeMemory] = []
        async with httpx.AsyncClient(headers=self._headers, timeout=30.0) as client:
            memories.extend(await self._ingest_issues(client, repo, since, limit))
            memories.extend(await self._ingest_pr_reviews(client, repo, limit))
        return memories

    async def _ingest_issues(
        self,
        client: httpx.AsyncClient,
        repo: str,
        since: str | None,
        limit: int,
    ) -> list[CodeMemory]:
        """Fetch bug-labelled issues and convert to CodeMemory."""
        params: dict[str, Any] = {
            "labels": "bug",
            "state": "closed",
            "per_page": min(limit, 100),
        }
        if since:
            params["since"] = since

        try:
            response = await client.get(
                f"{GITHUB_API}/repos/{repo}/issues", params=params
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("GitHub issues fetch failed: %s", exc)
            return []

        memories: list[CodeMemory] = []
        for issue in response.json():
            labels = [lb["name"] for lb in issue.get("labels", [])]
            title = issue.get("title", "")
            body = issue.get("body") or ""
            number = issue.get("number", 0)
            url = issue.get("html_url", "")

            narrative = (
                f"GitHub issue #{number} in {repo}: '{title}'. "
                f"Description: {body[:800]}. "
                f"Labels: {', '.join(labels)}."
            )

            memories.append(
                CodeMemory(
                    source="github",
                    memory_type="bug",
                    narrative=narrative,
                    category=_infer_category(labels),
                    severity=_infer_severity(labels),
                    tags=labels + ["github-issue", repo],
                    source_url=url,
                    root_cause=title,
                    lessons=[f"GitHub issue: {title}"],
                )
            )
        return memories

    async def _ingest_pr_reviews(
        self,
        client: httpx.AsyncClient,
        repo: str,
        limit: int,
    ) -> list[CodeMemory]:
        """Fetch recent PR review comments and convert to CodeMemory."""
        params: dict[str, Any] = {"per_page": min(limit, 100)}
        try:
            response = await client.get(
                f"{GITHUB_API}/repos/{repo}/pulls/comments", params=params
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("GitHub PR comments fetch failed: %s", exc)
            return []

        memories: list[CodeMemory] = []
        for comment in response.json():
            body = comment.get("body") or ""
            if not body.strip():
                continue
            path = comment.get("path", "")
            url = comment.get("html_url", "")
            user = comment.get("user", {}).get("login", "unknown")

            narrative = (
                f"PR review comment by {user} on {repo}/{path}: {body[:800]}"
            )
            memories.append(
                CodeMemory(
                    source="github",
                    memory_type="review",
                    narrative=narrative,
                    file_path=path,
                    severity=Severity.MEDIUM,
                    tags=["github-pr-review", repo],
                    source_url=url,
                    lessons=[body[:200]],
                )
            )
        return memories
