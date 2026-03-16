"""ForgeMind CLI entry point.

Exposes developer-facing commands for ingesting data, generating code,
inspecting memory, running evolution analysis, and launching the dashboard.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="forgemind",
    help="ForgeMind — the coding agent that never makes the same mistake twice.",
    no_args_is_help=True,
)
ingest_app = typer.Typer(help="Ingest data from various sources.")
memory_app = typer.Typer(help="Inspect and manage memory spaces.")
app.add_typer(ingest_app, name="ingest")
app.add_typer(memory_app, name="memory")

console = Console()
err_console = Console(stderr=True)


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Ingest commands
# ---------------------------------------------------------------------------


@ingest_app.command("github")
def ingest_github(
    repo: str = typer.Option(..., help="GitHub repo in 'owner/name' format"),
    since: str | None = typer.Option(None, help="ISO date to filter since (e.g. 2026-01-01)"),
    limit: int = typer.Option(50, help="Max number of items to ingest"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Ingest bugs, PR reviews, and Actions failures from a GitHub repository."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.ingestors.github import GitHubIngestor
        from src.memory.client import EverMemOSClient
        from src.memory.ingestion import ingest_batch

        ingestor = GitHubIngestor()
        raw = {"repo": repo, "since": since, "limit": limit}
        console.print(f"[cyan]Ingesting from GitHub: {repo}[/cyan]")
        memories = await ingestor.ingest(raw)
        console.print(f"[green]Parsed {len(memories)} memories[/green]")

        async with EverMemOSClient() as client:
            results = await ingest_batch(memories, client)
        console.print(f"[bold green]✓ Stored {len(results)} memories[/bold green]")

    asyncio.run(_run())


@ingest_app.command("coderabbit")
def ingest_coderabbit(
    file: Path = typer.Argument(..., help="Path to CodeRabbit JSON review file"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Ingest a CodeRabbit review JSON file."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.ingestors.coderabbit import CodeRabbitIngestor
        from src.memory.client import EverMemOSClient
        from src.memory.ingestion import ingest_batch

        ingestor = CodeRabbitIngestor()
        memories = await ingestor.ingest(file)
        console.print(f"[green]Parsed {len(memories)} memories[/green]")
        async with EverMemOSClient() as client:
            results = await ingest_batch(memories, client)
        console.print(f"[bold green]✓ Stored {len(results)} memories[/bold green]")

    asyncio.run(_run())


@ingest_app.command("linter")
def ingest_linter(
    file: Path = typer.Argument(..., help="Path to linter output file"),
    tool: str = typer.Option("ruff", help="Linter tool name (ruff, eslint, mypy, etc.)"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Ingest linter output (ruff, ESLint, mypy, pylint)."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.ingestors.linter import LinterIngestor
        from src.memory.client import EverMemOSClient
        from src.memory.ingestion import ingest_batch

        ingestor = LinterIngestor(tool=tool)
        memories = await ingestor.ingest(file)
        console.print(f"[green]Parsed {len(memories)} memories[/green]")
        async with EverMemOSClient() as client:
            results = await ingest_batch(memories, client)
        console.print(f"[bold green]✓ Stored {len(results)} memories[/bold green]")

    asyncio.run(_run())


@ingest_app.command("generic")
def ingest_generic(
    file: Path = typer.Argument(..., help="Path to raw tool output file"),
    source: str = typer.Option("generic", help="Source label for the memories"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Ingest any raw tool output via LLM extraction (BugBot, Macroscope, etc.)."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.ingestors.generic import GenericIngestor
        from src.memory.client import EverMemOSClient
        from src.memory.ingestion import ingest_batch

        ingestor = GenericIngestor(source=source)
        memories = await ingestor.ingest(file)
        console.print(f"[green]Parsed {len(memories)} memories[/green]")
        async with EverMemOSClient() as client:
            results = await ingest_batch(memories, client)
        console.print(f"[bold green]✓ Stored {len(results)} memories[/bold green]")

    asyncio.run(_run())


@ingest_app.command("pytest")
def ingest_pytest(
    file: Path = typer.Argument(..., help="Path to pytest output (.txt or .xml)"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Ingest pytest failure output (plain text or JUnit XML)."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.ingestors.pytest_ingestor import PytestIngestor
        from src.memory.client import EverMemOSClient
        from src.memory.ingestion import ingest_batch

        ingestor = PytestIngestor()
        memories = await ingestor.ingest(file)
        console.print(f"[green]Parsed {len(memories)} memories[/green]")
        async with EverMemOSClient() as client:
            results = await ingest_batch(memories, client)
        console.print(f"[bold green]✓ Stored {len(results)} memories[/bold green]")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Generate command
# ---------------------------------------------------------------------------


@app.command("generate")
def generate(
    task: str | None = typer.Option(None, "--task", help="Natural language task description"),
    task_file: Path | None = typer.Option(None, "--task-file", help="Path to task markdown file"),
    lang: str = typer.Option("python", "--lang", help="Target programming language"),
    output: Path | None = typer.Option(None, "--output", help="Write generated code to file"),
    context: str | None = typer.Option(None, "--context", help="Additional context"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Generate code with memory-informed context."""
    _setup_logging(log_level)
    if not task and not task_file:
        err_console.print("[red]Provide --task or --task-file[/red]")
        raise typer.Exit(1)

    task_text = task or (task_file.read_text() if task_file else "")

    async def _run() -> None:
        from src.forge.generator import CodeGenerator
        from src.memory.client import EverMemOSClient
        from src.schemas.generation import CodeRequest

        request = CodeRequest(task=task_text, language=lang, context=context)
        generator = CodeGenerator()

        async with EverMemOSClient() as client:
            result, attempts = await generator.generate_with_retry(request, client)

        console.print(f"\n[bold cyan]Generated code[/bold cyan] (confidence={result.confidence:.2f}):\n")
        console.print(result.code)

        if result.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for w in result.warnings:
                console.print(f"  • {w}")

        if output:
            output.write_text(result.code)
            console.print(f"\n[green]Code written to {output}[/green]")

        console.print(f"\n[dim]Attempts: {'; '.join(attempts)}[/dim]")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Memory commands
# ---------------------------------------------------------------------------


@memory_app.command("stats")
def memory_stats(
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Show memory space statistics."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.memory.client import MEMORY_SPACES, EverMemOSClient

        async with EverMemOSClient() as client:
            console.print("[bold]Memory Space Statistics[/bold]\n")
            for space in MEMORY_SPACES:
                try:
                    hits = await client.search_memories(
                        query="*", space_id=space, retrieve_method="keyword", top_k=1
                    )
                    console.print(f"  {space:<32} {len(hits):>4} memories (sample)")
                except Exception as exc:
                    console.print(f"  {space:<32} [red]error: {exc}[/red]")

    asyncio.run(_run())


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Search query"),
    space: str | None = typer.Option(None, help="Restrict to a specific memory space"),
    method: str = typer.Option("hybrid", help="Retrieval method"),
    top_k: int = typer.Option(10, help="Number of results"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Search across memory spaces."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.memory.client import EverMemOSClient

        async with EverMemOSClient() as client:
            hits = await client.search_memories(
                query=query, space_id=space, retrieve_method=method, top_k=top_k
            )
        console.print(f"\n[bold]Search results for:[/bold] {query!r}\n")
        for i, hit in enumerate(hits, 1):
            content = (
                hit.get("content")
                or hit.get("text")
                or hit.get("message", {}).get("content", str(hit))
            )
            console.print(f"[{i}] {content[:200]}\n")

    asyncio.run(_run())


@memory_app.command("export")
def memory_export(
    space: str = typer.Option(..., help="Memory space to export"),
    output: Path | None = typer.Option(None, help="Output JSON file path"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Export memories from a space to JSON."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.memory.client import EverMemOSClient

        async with EverMemOSClient() as client:
            hits = await client.search_memories(
                query="*", space_id=space, retrieve_method="keyword", top_k=100
            )
        data = json.dumps(hits, indent=2, default=str)
        if output:
            output.write_text(data)
            console.print(f"[green]Exported {len(hits)} memories to {output}[/green]")
        else:
            console.print(data)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Evolution & dashboard commands
# ---------------------------------------------------------------------------


@app.command("evolve")
def evolve(
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Run the strategist/evolution analysis cycle."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.gardener.strategist import Strategist
        from src.memory.client import EverMemOSClient

        async with EverMemOSClient() as client:
            strategist = Strategist()
            strategies = await strategist.run(client)
        console.print(f"[bold green]✓ Derived {len(strategies)} strategies[/bold green]")
        for s in strategies:
            console.print(f"  • [bold]{s.name}[/bold]: {s.description[:80]}")

    asyncio.run(_run())


@app.command("report")
def report(
    format: str = typer.Option("text", help="Output format: text | markdown"),
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Show the ForgeMind evolution report."""
    _setup_logging(log_level)
    from src.gardener.report import generate_markdown_report, generate_text_report
    from src.schemas.evolution import AgentState

    state = AgentState()
    if format == "markdown":
        console.print(generate_markdown_report(state))
    else:
        console.print(generate_text_report(state))


@app.command("dashboard")
def dashboard(
    log_level: str = typer.Option("INFO", envvar="FORGEMIND_LOG_LEVEL"),
) -> None:
    """Launch the terminal dashboard."""
    _setup_logging(log_level)

    async def _run() -> None:
        from src.dashboard.app import run_dashboard
        from src.gardener.evolution import EvolutionTracker
        from src.memory.client import EverMemOSClient

        tracker = EvolutionTracker()
        async with EverMemOSClient() as client:
            await run_dashboard(client, tracker)

    asyncio.run(_run())


if __name__ == "__main__":
    app()
