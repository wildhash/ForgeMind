# ForgeMind 🔥🧠

> **The coding agent that never makes the same mistake twice.**

[![EverMemOS Memory Genesis 2026](https://img.shields.io/badge/EverMemOS-Memory%20Genesis%202026-purple)](https://evermind.ai)
[![Track 1: Agent + Memory](https://img.shields.io/badge/Track-Agent%20%2B%20Memory-blue)](https://evermind.ai)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-green)](https://python.org)

A self-improving software forge powered by EverMemOS that ingests every bug, code review, and workflow failure across your entire toolchain, then uses that accumulated intelligence to produce increasingly perfect code.

---

## The Problem

AI coding agents are **stateless amnesiacs**. They make the same mistakes in every session.

- CodeRabbit catches the same patterns your team has seen 100 times before
- CI fails on bugs you fixed last week — and the week before
- Copilot suggests code that your senior engineers know is wrong
- Every new PR starts with zero institutional knowledge

There is no learning. There is no memory. There is only eternal recurrence.

---

## The Solution

**ForgeMind gives your coding agent a hippocampus.**

Every bug, code review, CI/CD failure, and workflow outcome becomes permanent semantic memory via **EverMemOS**. Each generation of code is born from the accumulated wisdom of everything that came before.

```
INGEST → REMEMBER → GENERATE → VERIFY → LEARN → REMEMBER (better)
```

The agent stores its own successes and failures, creating a recursive self-improvement loop. With every cycle, the generation baseline rises. **This is compounding intelligence applied to software engineering.**

---

## Architecture

### The Core Loop

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   INGEST    │───▶│   REMEMBER   │───▶│  GENERATE   │
│             │    │  (EverMemOS) │    │  (Claude)   │
│ GitHub      │    │              │    │             │
│ CodeRabbit  │    │ 6 isolated   │    │ Memory-     │
│ pytest      │    │ memory       │    │ informed    │
│ ruff/ESLint │    │ spaces       │    │ prompts     │
│ git history │    │              │    │             │
└─────────────┘    └──────────────┘    └──────┬──────┘
                                              │
┌─────────────┐    ┌──────────────┐           │
│  REMEMBER   │◀───│    LEARN     │◀──────────┘
│  (better)   │    │              │    ┌─────────────┐
│             │    │ success →    │    │   VERIFY    │
│ Memory      │    │ pattern      │    │             │
│ grows each  │    │ failure →    │    │ ruff, mypy  │
│ cycle       │    │ bug memory   │    │ pytest      │
└─────────────┘    └──────────────┘    └─────────────┘
```

### Memory Space Architecture

ForgeMind uses **6 isolated EverMemOS memory spaces**, each serving a distinct cognitive function:

| Space | Purpose |
|-------|---------|
| `forgemind-bugs` | Every bug ever encountered — root cause, fix, category |
| `forgemind-reviews` | Code review feedback — patterns of critique |
| `forgemind-patterns` | Positive patterns — architectures and idioms that worked |
| `forgemind-failures` | CI/CD and runtime failures — stack traces, env issues |
| `forgemind-strategies` | Meta-strategies — which approaches work for which problems |
| `forgemind-evolution` | The agent's own evolution log — what it learned and when |

### Module Map

```
src/
├── config.py              # Pydantic Settings
├── schemas/               # Type-safe data models
│   ├── memory.py          # CodeMemory, BugCategory, Severity, ...
│   ├── generation.py      # CodeRequest, CodeResult, VerificationResult
│   └── evolution.py       # EvolutionEntry, StrategyProfile, AgentState
├── memory/                # EverMemOS integration
│   ├── client.py          # Async REST client with retry logic
│   ├── spaces.py          # Space management
│   ├── ingestion.py       # Memory storage pipeline
│   └── recall.py          # Semantic retrieval + context assembly
├── ingestors/             # Tool-specific parsers
│   ├── github.py          # GitHub Issues, PRs, Actions
│   ├── coderabbit.py      # CodeRabbit reviews
│   ├── linter.py          # ruff, ESLint, mypy
│   ├── pytest_ingestor.py # pytest failures
│   ├── git_history.py     # Bug-fix commit analysis
│   └── generic.py         # LLM-powered catch-all parser ⭐
├── forge/                 # Generation engine
│   ├── prompts.py         # Prompt templates
│   ├── generator.py       # Claude + memory → code
│   ├── verifier.py        # Lint/type/test verification
│   └── learner.py         # Post-generation memory capture
├── gardener/              # Meta-intelligence
│   ├── ranker.py          # Memory relevance scoring
│   ├── strategist.py      # Strategy derivation
│   ├── evolution.py       # Improvement tracking
│   └── report.py          # Evolution reports
└── dashboard/
    └── app.py             # Rich terminal dashboard
```

---

## Supported Tools

| Tool | Ingestor | Type |
|------|----------|------|
| GitHub Issues & PRs | `github.py` | Bugs, reviews |
| GitHub Actions | `github.py` | Failures |
| CodeRabbit | `coderabbit.py` | Reviews |
| GitHub Copilot | `copilot.py` | Patterns |
| ruff / ESLint / mypy | `linter.py` | Lint errors |
| pytest | `pytest_ingestor.py` | Test failures |
| Git history | `git_history.py` | Bug-fix commits |
| **Any tool** (BugBot, Macroscope, CharlieHelps, InfinitiCode) | `generic.py` ⭐ | Universal |

> **The Generic Ingestor** is the killer feature. Paste any raw tool output, and Claude extracts structured code intelligence. No integration required. ForgeMind works with every tool on day one.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/wildhash/ForgeMind
cd ForgeMind
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env with your EverMemOS and Anthropic API keys

# 3. Ingest your first bugs
forgemind ingest github --repo owner/my-repo --since 2026-01-01

# 4. Generate memory-informed code
forgemind generate --task "Write an async HTTP client with retry logic" --lang python

# 5. Watch the agent evolve
forgemind evolve
forgemind report
forgemind dashboard
```

---

## Demo

### Step 1: Ingest 50 GitHub bugs from a popular repo

```bash
forgemind ingest github --repo pallets/flask --since 2025-01-01 --limit 50
# ✓ Stored 47 memories in forgemind-bugs and forgemind-reviews
```

### Step 2: Generate code with memory context

```bash
forgemind generate \
  --task "Write an async route handler that parses JSON and validates required fields" \
  --lang python

# MEMORY BRIEFING:
# Based on 12 relevant memories: Flask route handlers frequently fail with
# KeyError when accessing request.json without checking for None first.
# Pattern: always use request.get_json(silent=True) with None guard.
#
# Generated code (confidence=0.94):
# @app.route('/users', methods=['POST'])
# async def create_user():
#     data = request.get_json(silent=True)
#     if data is None:
#         return jsonify({"error": "Invalid or missing JSON body"}), 400
#     ...
```

### Step 3: Watch evolution after 10 cycles

```bash
forgemind report
# ForgeMind Evolution Report
# Evolution Score: 78.0%  Trend: 📈 improving
# Success rate: 8/10 generations passed verification
```

---

## EverMemOS Memory Genesis 2026 — Track 1: Agent + Memory

ForgeMind demonstrates that **long-term semantic memory is the missing primitive** for software engineering agents.

Key innovations:
1. **Narrative-first memory**: Rich natural language descriptions optimised for EverMemOS semantic search
2. **6-space cognitive architecture**: Bugs, reviews, patterns, failures, strategies, and evolution stored separately to prevent cross-contamination
3. **Self-referential learning**: The agent stores its own generation outcomes, creating recursive improvement
4. **The Generic Ingestor**: LLM-powered universal parser makes ForgeMind work with any tool immediately
5. **Evolution metrics**: Hard evidence that memory improves code quality — not a claim, a measurement

---

## Future Roadmap

- **BotSpot.trade integration**: Deploy ForgeMind as a tradeable bot that improves with community memory
- **Multi-agent ForgeMinds**: Multiple agents sharing a common EverMemOS memory pool — collective intelligence
- **Enterprise deployment**: Team-wide memory spaces so every engineer benefits from every bug
- **Cross-language memory**: Transfer bug patterns across Python → TypeScript → Rust

---

## License

MIT
