"""Terminal dashboard for ForgeMind using the rich library.

Displays memory stats, top bug categories, generation success rate,
and the evolution curve in a live terminal UI.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.gardener.evolution import EvolutionTracker
from src.memory.client import MEMORY_SPACES, EverMemOSClient
from src.schemas.evolution import AgentState

logger = logging.getLogger(__name__)
console = Console()


def _build_memory_table(memories_by_space: dict[str, int]) -> Table:
    """Build a Rich table of memory space statistics."""
    table = Table(title="Memory Spaces", show_header=True, header_style="bold cyan")
    table.add_column("Space", style="dim", min_width=24)
    table.add_column("Memories", justify="right")
    for space in MEMORY_SPACES:
        count = memories_by_space.get(space, 0)
        table.add_row(space, str(count))
    return table


def _build_stats_panel(state: AgentState) -> Panel:
    """Build a Rich panel with key generation statistics."""
    lines = [
        f"[bold]Evolution Score:[/bold]  {state.evolution_score:.1%}",
        f"[bold]Trend:[/bold]            {state.trend.value}",
        f"[bold]Total Generations:[/bold] {state.total_generations}",
        f"[bold]Success Rate:[/bold]     {state.generation_success_rate:.1%}",
    ]
    content = "\n".join(lines)
    return Panel(content, title="[bold green]ForgeMind Stats[/bold green]", padding=(1, 2))


def _build_categories_panel(top_categories: list[str]) -> Panel:
    """Build a Rich panel showing top bug categories."""
    if not top_categories:
        content = "[dim]No categories yet[/dim]"
    else:
        content = "\n".join(f"• {cat}" for cat in top_categories[:8])
    return Panel(content, title="[bold red]Top Bug Categories[/bold red]", padding=(1, 2))


def _build_strategies_panel(strategies: list[str]) -> Panel:
    """Build a Rich panel showing active strategies."""
    if not strategies:
        content = "[dim]No strategies yet[/dim]"
    else:
        content = "\n".join(f"→ {s[:70]}" for s in strategies[:5])
    return Panel(content, title="[bold yellow]Active Strategies[/bold yellow]", padding=(1, 2))


async def _fetch_dashboard_data(
    client: EverMemOSClient,
    tracker: EvolutionTracker,
) -> AgentState:
    """Fetch live data to populate the dashboard."""
    state = tracker.get_current_state()
    state.snapshot_at = datetime.now(UTC)

    # Count memories per space via lightweight search
    for space in MEMORY_SPACES:
        try:
            hits = await client.search_memories(
                query="*",
                space_id=space,
                retrieve_method="keyword",
                top_k=1,
            )
            # Use total_count if returned, else hits length
            state.memories_by_space[space] = len(hits)
        except Exception:
            state.memories_by_space.setdefault(space, 0)

    state.total_memories = sum(state.memories_by_space.values())
    return state


def render_static_dashboard(state: AgentState) -> None:
    """Render a one-shot static dashboard to the terminal."""
    console.print()
    console.print("[bold magenta]━━━ ForgeMind Dashboard ━━━[/bold magenta]")
    console.print()

    mem_table = _build_memory_table(state.memories_by_space)
    stats_panel = _build_stats_panel(state)
    cats_panel = _build_categories_panel(state.top_bug_categories)
    strats_panel = _build_strategies_panel(state.active_strategies)

    console.print(Columns([stats_panel, cats_panel]))
    console.print(mem_table)
    console.print(strats_panel)
    console.print()


async def run_dashboard(client: EverMemOSClient, tracker: EvolutionTracker) -> None:
    """Run a refreshing live dashboard.

    Refreshes every 5 seconds. Press Ctrl+C to exit.
    """
    console.print("[dim]Press Ctrl+C to exit the dashboard.[/dim]")
    try:
        while True:
            state = await _fetch_dashboard_data(client, tracker)
            console.clear()
            render_static_dashboard(state)
            await asyncio.sleep(5)
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("[dim]Dashboard closed.[/dim]")
