"""Post-verification learning module.

After every generation cycle, this module captures either:
- A success pattern (what worked and why) → stored in forgemind-patterns
- A failure memory (what went wrong) → stored in forgemind-bugs / forgemind-failures
"""

from __future__ import annotations

import logging

from src.memory.client import EverMemOSClient
from src.memory.ingestion import ingest_memory
from src.schemas.generation import CodeRequest, CodeResult, VerificationResult
from src.schemas.memory import BugCategory, CodeMemory, Severity

logger = logging.getLogger(__name__)


class Learner:
    """Capture generation outcomes as new EverMemOS memories."""

    async def learn(
        self,
        request: CodeRequest,
        result: CodeResult,
        verification: VerificationResult,
        client: EverMemOSClient,
    ) -> CodeMemory:
        """Store the generation outcome as a new memory.

        If verification passed, store a positive pattern.
        If it failed, store a bug/failure memory.

        Returns the CodeMemory that was stored.
        """
        if verification.passed:
            return await self._store_success(request, result, verification, client)
        return await self._store_failure(request, result, verification, client)

    async def _store_success(
        self,
        request: CodeRequest,
        result: CodeResult,
        verification: VerificationResult,
        client: EverMemOSClient,
    ) -> CodeMemory:
        """Store a successful generation as a positive pattern."""
        narrative = (
            f"Successful code generation for task: '{request.task[:200]}'. "
            f"Language: {request.language}. "
            f"Confidence: {result.confidence:.2f}. "
            f"Verification score: {verification.overall_score:.2f}. "
            f"Reasoning: {result.reasoning[:400]}. "
            f"Generated code snippet: {result.code[:400]}"
        )
        memory = CodeMemory(
            source="forgemind-generator",
            memory_type="pattern",
            narrative=narrative,
            language=request.language,
            file_path=request.file_path,
            severity=Severity.INFO,
            tags=["generation-success", request.language] + (
                ["high-confidence"] if result.confidence >= 0.8 else []
            ),
            lessons=[
                f"Task '{request.task[:100]}' generated successfully with score {verification.overall_score:.2f}",
                result.reasoning[:200],
            ],
            code_after=result.code[:1000],
        )
        await ingest_memory(memory, client, space_id="forgemind-patterns")
        logger.info("Stored success pattern memory %s", memory.id)
        return memory

    async def _store_failure(
        self,
        request: CodeRequest,
        result: CodeResult,
        verification: VerificationResult,
        client: EverMemOSClient,
    ) -> CodeMemory:
        """Store a generation failure as a bug/failure memory."""
        errors = verification.lint_errors[:3] + verification.type_errors[:3]
        error_summary = "; ".join(errors) if errors else "unknown errors"

        narrative = (
            f"Code generation failure for task: '{request.task[:200]}'. "
            f"Language: {request.language}. "
            f"Verification score: {verification.overall_score:.2f}. "
            f"Errors: {error_summary}. "
            f"Generated code snippet: {result.code[:400]}"
        )
        memory = CodeMemory(
            source="forgemind-generator",
            memory_type="failure",
            narrative=narrative,
            language=request.language,
            file_path=request.file_path,
            category=BugCategory.LOGIC_ERROR,
            severity=Severity.HIGH,
            tags=["generation-failure", request.language],
            root_cause=error_summary[:200],
            lessons=[
                f"Task '{request.task[:100]}' failed verification",
                f"Errors: {error_summary[:200]}",
            ],
            code_before=result.code[:1000],
        )
        await ingest_memory(memory, client, space_id="forgemind-failures")
        logger.info("Stored failure memory %s", memory.id)
        return memory
