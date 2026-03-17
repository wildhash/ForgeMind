# CLAUDE.md — ForgeMind

## IDENTITY

ForgeMind is a self-improving agentic coding system powered by EverMemOS long-term memory. It ingests bugs, code reviews, CI/CD failures, linting errors, and workflow outcomes from every tool in a developer's ecosystem — CodeRabbit, GitHub Copilot, BugBot, Macroscope, InfinitiCode, CharlieHelps, ESLint, pytest, and raw git history — then uses that accumulated intelligence to produce increasingly perfect code with each generation.

ForgeMind is a submission for the EverMemOS Memory Genesis 2026 hackathon, Track 1: Agent + Memory. It demonstrates that long-term semantic memory transforms a stateless code generator into a self-evolving software forge where every failure makes the next output structurally better.

**Thesis**: Software bugs are not random. They cluster around the same conceptual mistakes — misunderstood APIs, off-by-one boundaries, missing null checks, race conditions, wrong assumptions about state. A coding agent that REMEMBERS every bug it has ever seen, WHY it happened, and HOW it was fixed, will converge toward producing code that avoids those entire categories of error. This is not autocomplete. This is compounding intelligence applied to software engineering.

## PROJECT RULES

1. **Plan Mode first**: Before writing ANY code, output a numbered plan. Verify the plan addresses the task. Then execute step by step.
2. **Feedback loops**: After creating any file, verify it — run `python -c "import module"` for Python files, run `npx tsc --noEmit` for TypeScript, run linters where configured. Fix errors before moving on.
3. **One file, one responsibility**: Every module does one thing. No god files.
4. **Type everything**: Full type hints on every Python function signature. Use dataclasses or Pydantic for all schemas.
5. **Docstrings on every public function**: Brief, purpose-focused.
6. **Tests alongside code**: When building a module, write at least one test for its core behavior in `tests/`.
7. **Update this file**: If you discover a mistake pattern while building, add it to the MISTAKES section below.

## MISTAKES LOG

(Claude Code: append to this section whenever you encounter and fix a recurring issue during build)

- (none yet — this section grows as the project evolves)

## TECH STACK

- **Language**: Python 3.11+
- **Memory**: EverMemOS Cloud API (REST) — see `memory/client.py`
- **LLM**: Anthropic Claude API for code generation and analysis — model `claude-sonnet-4-20250514`
- **Package management**: `uv` (preferred) or `pip`
- **Config**: `.env` file via `python-dotenv`, Pydantic Settings for validation
- **HTTP**: `httpx` (async)
- **CLI**: `typer` for developer-facing commands
- **Testing**: `pytest` + `pytest-asyncio`
- **Linting**: `ruff`
- **Git integration**: `gitpython`

## ARCHITECTURE

### The Core Loop
INGEST → REMEMBER → GENERATE → VERIFY → LEARN → REMEMBER (better)

ForgeMind operates on a continuous improvement cycle:

1. **INGEST**: Pull bugs, reviews, failures from external tools into structured `CodeMemory` objects
2. **REMEMBER**: Store them in EverMemOS with rich semantic metadata across isolated memory spaces
3. **GENERATE**: When asked to write code, query memory for all relevant past failures, patterns, and lessons — inject them as context alongside the task
4. **VERIFY**: Run the generated code through linters, type checkers, tests, and optionally external review tools
5. **LEARN**: If verification fails, capture the failure as a new memory. If it succeeds, capture what worked.
6. **REMEMBER (better)**: The memory grows. Next generation starts from a higher baseline.

### Memory Space Architecture

ForgeMind uses 6 isolated EverMemOS memory spaces. Each serves a distinct cognitive function:
```
"forgemind-bugs"           # Every bug ever encountered — root cause, fix, category
"forgemind-reviews"        # Code review feedback — what reviewers caught, patterns of critique
"forgemind-patterns"       # Positive patterns — architectures, idioms, approaches that worked
"forgemind-failures"       # CI/CD and runtime failures — stack traces, environment issues, config bugs
"forgemind-strategies"     # Meta-strategies — which approaches work for which problem types
"forgemind-evolution"      # The agent's own evolution log — what it learned, when, from what
```

### File Structure
```
forgemind/
├── CLAUDE.md                      # This file — the project blueprint
├── README.md                      # Hackathon-facing readme with demo, screenshots, setup
├── pyproject.toml                 # uv/pip project config, dependencies, ruff config
├── .env.example                   # Template for API keys
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point via typer
│   ├── config.py                  # Pydantic Settings, env loading
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── memory.py              # CodeMemory, BugReport, ReviewFeedback, FailureEvent, etc.
│   │   ├── generation.py          # CodeRequest, CodeResult, VerificationResult
│   │   └── evolution.py           # EvolutionEntry, StrategyProfile, AgentState
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── client.py              # EverMemOS Cloud API wrapper (async httpx)
│   │   ├── spaces.py              # Memory space management, initialization
│   │   ├── ingestion.py           # Transform raw tool output → CodeMemory → EverMemOS
│   │   └── recall.py              # Semantic search, multi-hop queries, context assembly
│   │
│   ├── ingestors/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract base ingestor interface
│   │   ├── github.py              # GitHub Issues, PRs, Actions logs
│   │   ├── coderabbit.py          # CodeRabbit review comments
│   │   ├── copilot.py             # Copilot suggestions + acceptance/rejection patterns
│   │   ├── linter.py              # ESLint, ruff, mypy, pylint output parsing
│   │   ├── pytest_ingestor.py     # pytest failure parsing (avoid name collision with pytest)
│   │   ├── git_history.py         # Git log analysis — bug-fix commits, reverts, patterns
│   │   └── generic.py             # Paste-in raw text (for CharlieHelps, BugBot, Macroscope, etc.)
│   │
│   ├── forge/
│   │   ├── __init__.py
│   │   ├── generator.py           # LLM-powered code generation with memory-informed prompts
│   │   ├── verifier.py            # Run generated code through linters, type check, tests
│   │   ├── learner.py             # Post-verification: capture success/failure as new memories
│   │   └── prompts.py             # Prompt templates for generation, analysis, review
│   │
│   ├── gardener/
│   │   ├── __init__.py
│   │   ├── ranker.py              # Score and rank memories by relevance, recency, impact
│   │   ├── strategist.py          # Meta-agent: analyzes memory landscape, identifies gaps
│   │   ├── evolution.py           # Track agent improvement over time
│   │   └── report.py              # Generate evolution reports — what's improved, what hasn't
│   │
│   └── dashboard/
│       ├── __init__.py
│       └── app.py                 # Simple terminal-based dashboard (rich library)
│
└── tests/
    ├── __init__.py
    ├── conftest.py                # Shared fixtures, mock EverMemOS responses
    ├── test_schemas.py            # Schema validation tests
    ├── test_memory_client.py      # EverMemOS client tests (mocked)
    ├── test_ingestion.py          # Ingestor parsing tests
    ├── test_generator.py          # Code generation pipeline tests
    ├── test_verifier.py           # Verification pipeline tests
    └── test_evolution.py          # Evolution tracking tests
```

## DETAILED MODULE SPECIFICATIONS

### 1. `src/config.py`
Uses `pydantic_settings.BaseSettings` with `.env` file support. Validates that required keys are present at startup. Provides sensible defaults for optional values.

### 2. `src/schemas/memory.py`
Core data structures: `CodeMemory`, `BugCategory`, `Severity`, `ReviewFeedback`, `FailureEvent`, `EvolutionEntry`.

### 3. `src/memory/client.py`
Async wrapper around the EverMemOS Cloud REST API using `httpx.AsyncClient` with retry logic.

### 4. `src/memory/recall.py`
Intelligence layer on top of raw search — assembles `MemoryContext` for generation.

### 5. `src/forge/generator.py`
Core code generation engine: recall context → build prompt → call Claude → verify → learn.

## BUILD ORDER

Execute in this exact sequence:
1. `pyproject.toml` + `.env.example`
2. `src/config.py`
3. `src/schemas/memory.py`
4. `src/schemas/generation.py`
5. `src/schemas/evolution.py`
6. `src/memory/client.py`
7. `src/memory/spaces.py`
8. `src/memory/ingestion.py`
9. `src/memory/recall.py`
10. `src/ingestors/base.py`
11-16. All ingestors
17-20. `src/forge/` modules
21-24. `src/gardener/` modules
25. `src/dashboard/app.py`
26. `src/main.py`
27-33. All tests
34. `README.md`

## KEY DESIGN DECISIONS

1. **Narrative-first memory**: The `narrative` field is the most important field in CodeMemory.
2. **Memory spaces as cognitive separation**: 6 isolated spaces prevent cross-contamination.
3. **The Generic Ingestor is the killer feature**: LLM-extracts structured memory from ANY raw text.
4. **Self-referential learning**: The agent stores its OWN generation successes/failures as memories.
5. **Evolution as proof**: Hard evidence that memory improves code quality over time.
