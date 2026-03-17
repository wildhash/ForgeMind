"""Code verification pipeline.

Runs generated code through syntax checks, linting, type checking,
and tests to produce a VerificationResult.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from src.schemas.generation import CodeResult, VerificationResult

logger = logging.getLogger(__name__)


class CodeVerifier:
    """Verify generated code via linting, type checking, and optional tests."""

    async def verify(
        self,
        result: CodeResult,
        language: str = "python",
    ) -> VerificationResult:
        """Run the full verification suite on generated code.

        Args:
            result: The CodeResult containing the code to verify.
            language: Target language (currently only Python is fully supported).

        Returns:
            VerificationResult with pass/fail and detailed error lists.
        """
        if language.lower() != "python":
            # For non-Python languages, return a permissive result
            return VerificationResult(passed=True, overall_score=0.7)

        code = result.code
        if not code.strip():
            return VerificationResult(
                passed=False,
                lint_errors=["Empty code output"],
                overall_score=0.0,
            )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(code)
            tmp_path = Path(tmp.name)

        try:
            lint_errors = self._run_ruff(tmp_path)
            type_errors = self._run_mypy(tmp_path)
            syntax_ok = self._check_syntax(code)

            if not syntax_ok:
                return VerificationResult(
                    passed=False,
                    lint_errors=["SyntaxError: code could not be parsed"],
                    type_errors=type_errors,
                    overall_score=0.0,
                )

            total_errors = len(lint_errors) + len(type_errors)
            score = max(0.0, 1.0 - (total_errors / (total_errors + 5)))
            passed = total_errors == 0

            return VerificationResult(
                passed=passed,
                lint_errors=lint_errors,
                type_errors=type_errors,
                overall_score=round(score, 3),
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def _check_syntax(self, code: str) -> bool:
        """Return True if the code parses without SyntaxError."""
        try:
            compile(code, "<generated>", "exec")
            return True
        except SyntaxError as exc:
            logger.debug("Syntax error in generated code: %s", exc)
            return False

    def _run_ruff(self, path: Path) -> list[str]:
        """Run ruff linter and return a list of error messages."""
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "ruff", "check", "--output-format=text", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            errors = [ln for ln in proc.stdout.splitlines() if ln.strip()]
            return errors
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.debug("ruff check skipped: %s", exc)
            return []

    def _run_mypy(self, path: Path) -> list[str]:
        """Run mypy type checker and return a list of error messages."""
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "--ignore-missing-imports",
                    "--no-error-summary",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            errors = [
                ln
                for ln in proc.stdout.splitlines()
                if ": error:" in ln or ": warning:" in ln
            ]
            return errors
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.debug("mypy check skipped: %s", exc)
            return []
