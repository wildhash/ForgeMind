"""Prompt templates for ForgeMind code generation and analysis."""

from __future__ import annotations

GENERATION_SYSTEM = """\
You are ForgeMind, a coding agent with perfect memory. You have access to the
accumulated wisdom of every bug, code review, and failure your team has ever
encountered. Use this knowledge to write code that avoids known failure patterns
and follows proven best practices.

Respond with a JSON object containing exactly these keys:
- code (string): the complete generated code
- reasoning (string): why you wrote it this way, referencing specific memories
- memory_references (array of strings): IDs or short descriptions of memories that influenced output
- confidence (number 0-1): your confidence this code is correct
- warnings (array of strings): things you are unsure about or edge cases to watch

Return ONLY the JSON object. No markdown fences, no extra prose.
"""

GENERATION_USER_TEMPLATE = """\
MEMORY BRIEFING:
{memory_summary}

KNOWN BUG PATTERNS TO AVOID:
{formatted_bugs}

PROVEN PATTERNS TO FOLLOW:
{formatted_patterns}

REVIEW FEEDBACK ON SIMILAR CODE:
{formatted_reviews}

ACTIVE STRATEGIES:
{formatted_strategies}

TASK:
{task_description}

CONSTRAINTS:
- Language: {language}
- File path: {file_path}
- Must pass: {test_requirements}

Generate the code. Explain your reasoning. Reference which memories influenced
your decisions. Rate your confidence 0-1.
"""

ANALYSIS_SYSTEM = """\
You are a code intelligence analyst. Given a verification failure, extract a
structured description of what went wrong. Return JSON with keys:
- narrative (string): rich description of the failure
- category (string): bug category (logic_error | type_mismatch | etc.)
- severity (string): critical | high | medium | low
- root_cause (string): one-line root cause
- fix_pattern (string): reusable fix pattern
- lessons (array of strings): 1-3 takeaways
"""

STRATEGY_SYSTEM = """\
You are ForgeMind's meta-strategist. Analyse the provided memory landscape and
identify actionable strategies that should be applied during future code generation.

Each strategy should be a specific, actionable rule like:
"When generating async Python HTTP handlers, always include explicit timeout
parameters — X% of our async failures involved missing timeouts."

Return JSON with a key "strategies" containing an array of objects, each with:
- name (string): short strategy name
- description (string): the actionable rule
- applies_to (array of strings): languages or domains it applies to
- evidence_count (integer): number of memories supporting this strategy
- confidence (number 0-1): confidence in this strategy
"""


def format_memories_for_prompt(memories: list, max_per_memory: int = 400) -> str:
    """Format a list of CodeMemory objects into a prompt-ready string."""
    if not memories:
        return "(none)"
    lines: list[str] = []
    for i, m in enumerate(memories, 1):
        snippet = m.narrative[:max_per_memory]
        if m.root_cause:
            snippet += f" [Root cause: {m.root_cause}]"
        if m.fix_pattern:
            snippet += f" [Fix: {m.fix_pattern}]"
        lines.append(f"{i}. {snippet}")
    return "\n".join(lines)


def build_generation_prompt(
    task: str,
    language: str,
    file_path: str | None,
    test_requirements: str | None,
    memory_summary: str,
    bugs: list,
    patterns: list,
    reviews: list,
    strategies: list[str],
) -> str:
    """Assemble the full user-turn generation prompt."""
    return GENERATION_USER_TEMPLATE.format(
        memory_summary=memory_summary or "No prior memories available.",
        formatted_bugs=format_memories_for_prompt(bugs),
        formatted_patterns=format_memories_for_prompt(patterns),
        formatted_reviews=format_memories_for_prompt(reviews),
        formatted_strategies="\n".join(f"- {s}" for s in strategies) or "(none)",
        task_description=task,
        language=language,
        file_path=file_path or "not specified",
        test_requirements=test_requirements or "not specified",
    )
