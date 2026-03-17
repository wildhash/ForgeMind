"""LLM-powered code generation engine.

Implements the core GENERATE step of the ForgeMind loop:
recall context â†’ build prompt â†’ call Claude â†’ verify â†’ learn â†’ return.
"""

from __future__ import annotations

import json
import logging

import anthropic

from src.config import get_settings
from src.forge.prompts import GENERATION_SYSTEM, build_generation_prompt
from src.memory.client import EverMemOSClient
from src.memory.recall import assemble_context
from src.schemas.generation import CodeRequest, CodeResult, MemoryContext

logger = logging.getLogger(__name__)


def _parse_code_result(raw: str) -> CodeResult:
    """Parse the LLM JSON response into a CodeResult.

    Falls back gracefully if the LLM returns prose instead of JSON.
    """
    raw = raw.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        import re
        raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
        raw = raw.rstrip("`").strip()

    try:
        data = json.loads(raw)
        return CodeResult(
            code=data.get("code", ""),
            reasoning=data.get("reasoning", ""),
            memory_references=data.get("memory_references", []),
            confidence=float(data.get("confidence", 0.5)),
            warnings=data.get("warnings", []),
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        # Non-JSON response â€” treat the entire output as code
        logger.warning("LLM did not return JSON; treating output as raw code")
        return CodeResult(
            code=raw,
            reasoning="Raw code from LLM (non-JSON response)",
            confidence=0.3,
            warnings=["Response was not structured JSON â€” manual review recommended"],
        )


class CodeGenerator:
    """Core code generation engine powered by Claude + EverMemOS memory."""

    def __init__(self, memory_client: EverMemOSClient | None = None) -> None:
        """Initialise with an optional pre-opened memory client."""
        self._memory_client = memory_client

    async def generate(
        self,
        request: CodeRequest,
        memory_client: EverMemOSClient | None = None,
    ) -> CodeResult:
        """Generate code for the given request, informed by memory.

        Args:
            request: What to generate.
            memory_client: Open EverMemOSClient; falls back to self._memory_client.

        Returns:
            CodeResult with generated code, reasoning, and confidence.
        """
        client = memory_client or self._memory_client
        settings = get_settings()

        # Assemble memory context
        if client is not None:
            try:
                ctx = await assemble_context(request, client)
            except Exception as exc:
                logger.warning("Memory recall failed: %s â€” proceeding without memory", exc)
                ctx = MemoryContext()
        else:
            ctx = MemoryContext()

        # Build the generation prompt
        user_prompt = build_generation_prompt(
            task=request.task,
            language=request.language,
            file_path=request.file_path,
            test_requirements=request.test_requirements,
            memory_summary=ctx.memory_summary,
            bugs=ctx.relevant_bugs,
            patterns=ctx.relevant_patterns,
            reviews=ctx.relevant_reviews,
            strategies=ctx.active_strategies,
        )

        # Add any extra context from the request
        if request.context:
            user_prompt = f"ADDITIONAL CONTEXT:\n{request.context}\n\n{user_prompt}"

        # Call Claude
        anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = anthropic_client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=GENERATION_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_response = message.content[0].text

        result = _parse_code_result(raw_response)
        logger.info(
            "Generated code for task=%r confidence=%.2f warnings=%d",
            request.task[:60],
            result.confidence,
            len(result.warnings),
        )
        return result

    async def generate_with_retry(
        self,
        request: CodeRequest,
        memory_client: EverMemOSClient | None = None,
        max_retries: int | None = None,
    ) -> tuple[CodeResult, list[str]]:
        """Generate code with automatic retry on verification failure.

        Returns the final CodeResult and a list of attempt summaries.
        """
        from src.forge.verifier import CodeVerifier

        settings = get_settings()
        retries = max_retries if max_retries is not None else settings.forgemind_max_retries
        verifier = CodeVerifier()
        attempts: list[str] = []

        current_request = request
        for attempt in range(retries):
            result = await self.generate(current_request, memory_client)
            verification = await verifier.verify(result, request.language)

            attempts.append(
                f"Attempt {attempt + 1}: passed={verification.passed}, "
                f"score={verification.overall_score:.2f}"
            )

            if verification.passed:
                logger.info("Generation passed verification on attempt %d", attempt + 1)
                return result, attempts

            # Enrich the request with failure context for the next attempt
            failure_summary = (
                f"Previous attempt failed verification. "
                f"Lint errors: {'; '.join(verification.lint_errors[:3])}. "
                f"Type errors: {'; '.join(verification.type_errors[:3])}."
            )
            current_request = CodeRequest(
                task=request.task,
                language=request.language,
                context=(request.context or "") + "\n\nPREVIOUS FAILURE:\n" + failure_summary,
                file_path=request.file_path,
                test_requirements=request.test_requirements,
            )

        # If retries=0 or all retries failed, return the last generated result
        if not attempts:
            # No attempts were made (retries=0), generate once without verification
            result = await self.generate(current_request, memory_client)
            attempts.append("Attempt 1: passed=False (no verification performed)")

        logger.warning("All %d generation attempts failed verification", retries)
        return result, attempts

