"""Evolution report generator.

Produces human-readable reports about the agent's improvement over time.
"""

from __future__ import annotations

import logging

from src.schemas.evolution import AgentState, ImprovementTrend

logger = logging.getLogger(__name__)

_TREND_EMOJI: dict[ImprovementTrend, str] = {
    ImprovementTrend.IMPROVING: "📈",
    ImprovementTrend.STABLE: "➡️",
    ImprovementTrend.DEGRADING: "📉",
    ImprovementTrend.INSUFFICIENT_DATA: "❓",
}


def generate_text_report(state: AgentState) -> str:
    """Generate a plain-text evolution report from an AgentState snapshot.

    Args:
        state: The current agent state snapshot.

    Returns:
        A multi-line string suitable for terminal output.
    """
    trend_icon = _TREND_EMOJI.get(state.trend, "❓")
    lines = [
        "=" * 60,
        "  ForgeMind Evolution Report",
        f"  Generated: {state.snapshot_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        f"  Evolution Score:     {state.evolution_score:.1%}",
        f"  Trend:               {trend_icon} {state.trend.value}",
        "",
        "  Generation Stats",
        "  ----------------",
        f"  Total generations:   {state.total_generations}",
        f"  Successful:          {state.successful_generations}",
        f"  Success rate:        {state.generation_success_rate:.1%}",
        "",
    ]

    if state.memories_by_space:
        lines.append("  Memory Spaces")
        lines.append("  -------------")
        for space, count in state.memories_by_space.items():
            lines.append(f"  {space:<30} {count:>6} memories")
        lines.append("")

    if state.top_bug_categories:
        lines.append("  Top Bug Categories")
        lines.append("  ------------------")
        for cat in state.top_bug_categories:
            lines.append(f"  • {cat}")
        lines.append("")

    if state.active_strategies:
        lines.append("  Active Strategies")
        lines.append("  -----------------")
        for strategy in state.active_strategies[:5]:
            lines.append(f"  • {strategy[:80]}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def generate_markdown_report(state: AgentState) -> str:
    """Generate a Markdown evolution report.

    Args:
        state: The current agent state snapshot.

    Returns:
        A Markdown string for export or display.
    """
    trend_icon = _TREND_EMOJI.get(state.trend, "❓")
    parts = [
        "# ForgeMind Evolution Report",
        f"*Generated: {state.snapshot_at.strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## Summary",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Evolution Score | `{state.evolution_score:.1%}` |",
        f"| Trend | {trend_icon} {state.trend.value} |",
        f"| Total Generations | `{state.total_generations}` |",
        f"| Success Rate | `{state.generation_success_rate:.1%}` |",
        "",
    ]

    if state.memories_by_space:
        parts.append("## Memory Spaces")
        parts.append("| Space | Memories |")
        parts.append("|-------|----------|")
        for space, count in state.memories_by_space.items():
            parts.append(f"| `{space}` | {count} |")
        parts.append("")

    if state.top_bug_categories:
        parts.append("## Top Bug Categories")
        for cat in state.top_bug_categories:
            parts.append(f"- {cat}")
        parts.append("")

    if state.active_strategies:
        parts.append("## Active Strategies")
        for s in state.active_strategies[:5]:
            parts.append(f"- {s[:100]}")
        parts.append("")

    return "\n".join(parts)
