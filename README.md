# Mneva

> Persistent agent context substrate. Local-first markdown store that every AI tool can query.

[![PyPI](https://img.shields.io/pypi/v/mneva.svg)](https://pypi.org/project/mneva/)
[![Python versions](https://img.shields.io/pypi/pyversions/mneva.svg)](https://pypi.org/project/mneva/)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](./LICENSE)
[![CI](https://github.com/mneva-ai/mneva/actions/workflows/ci.yml/badge.svg)](https://github.com/mneva-ai/mneva/actions/workflows/ci.yml)
[![Install verify](https://github.com/mneva-ai/mneva/actions/workflows/install-verify.yml/badge.svg)](https://github.com/mneva-ai/mneva/actions/workflows/install-verify.yml)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)

mneva captures decisions, constraints, and state into plain markdown under
`~/.mneva/`, indexes them locally, and replays the result on demand into your
AI tool of choice. The same context follows you across Claude Code, Cursor,
Codex, and any other tool you wire it into. Everything stays on your machine.

## What it does

You work across Claude Code, Cursor, Codex, and a chat surface or two. Each
tool has its own context file: `CLAUDE.md`, `.cursor/rules/`, `AGENTS.md`. The
same decisions end up re-typed across all of them, and copies drift.

mneva keeps that context in one place: a local markdown store, a BM25 +
optional `sqlite-vec` index, and per-tool replay templates. Capture a record
once, replay it into whichever tool you are in.

## At a glance

```bash
pipx install mneva
mneva init
mneva capture --scope my-project --lifespan permanent \
    "decision: use SQLite over Postgres for v0 because zero-ops"
mneva search "SQLite"
mneva replay --tool=claude-code --scope=my-project
```

The last command prints a context block. Paste it into your Claude Code
session, or wire the same command into `CLAUDE.md` so Claude Code replays
it automatically every session (see
[Wire into your AI tool](#wire-into-your-ai-tool) below).

## Install

```bash
pipx install mneva
mneva --version
```

If `pipx` is not installed:

```bash
pip install --user pipx
python -m pipx ensurepath
# Close and reopen your terminal so PATH refreshes, then:
pipx install mneva
```

Alternative without `pipx`: `pip install --user mneva`. This installs into
your user site-packages and may conflict with pinned dependencies of other
tools, so `pipx` is preferred.

Requires Python 3.11 or newer.

## Quick start (60 seconds)

1. **Initialize the store.** Lands at `~/.mneva/` (override with
   `MNEVA_HOME=<path>`). Prints a one-time token; keep it if you plan to use
   `mneva serve` later.
   ```bash
   mneva init
   ```

2. **Capture a record.** `--scope` groups records by project or topic.
   `--lifespan permanent` survives across sessions; the default `transient`
   does not.
   ```bash
   mneva capture --scope my-project --lifespan permanent \
       "decision: use SQLite over Postgres for v0 because zero-ops"
   ```

3. **Check state.** Reports the indexed count and active mode (`sqlite-vec`
   if the wheel is available on your platform, BM25 otherwise).
   ```bash
   mneva status
   ```

4. **Search.** BM25 full-text by default; vector search runs alongside when
   `sqlite-vec` is loaded.
   ```bash
   mneva search "SQLite"
   ```

5. **Replay into your AI tool.** Emits a context block ready to paste.
   ```bash
   mneva replay --tool=claude-code --scope=my-project
   ```

Full walkthrough: [`docs/alpha-onboarding.md`](./docs/alpha-onboarding.md).

## Wire into your AI tool

Run `mneva replay --tool=<X> --scope=<Y>` once, then paste the output into
the tool's context file. After that, the tool auto-loads mneva context every
session.

| Tool        | Command                                         | Paste into                  |
|-------------|-------------------------------------------------|-----------------------------|
| Claude Code | `mneva replay --tool=claude-code --scope=<X>`   | `CLAUDE.md` (repo root)     |
| Cursor      | `mneva replay --tool=cursor --scope=<X>`        | `.cursor/rules/mneva.mdc`   |
| Codex       | `mneva replay --tool=codex --scope=<X>`         | `AGENTS.md` (repo root)     |

The Cursor template includes the YAML frontmatter Cursor requires.

## How it works

```
┌─────────┐     ┌──────────────────────┐     ┌──────────────────┐
│ capture │────▶│ ~/.mneva/            │     │ replay --tool=X  │
└─────────┘     │   markdown records   │────▶│ serve (HTTP API) │────▶  Claude Code
                │   + sqlite index     │     └──────────────────┘       Cursor
                └──────────────────────┘                                Codex
```

Records are plain markdown files with YAML frontmatter (scope, lifespan,
tool, source, id). The SQLite index is rebuilt from those files; the
markdown is the source of truth. `mneva serve` exposes the same operations
over an HTTP API on `127.0.0.1:7432`, gated by a per-store token.

## Commands

| Command            | Purpose                                                                |
|--------------------|------------------------------------------------------------------------|
| `mneva init`       | Initialize the store. Idempotent; safe to re-run.                      |
| `mneva capture`    | Add a record. `BODY` is positional; use `-` to read from stdin.        |
| `mneva search`     | BM25 + optional vector search. Filters: `--scope`, `--lifespan`, `-k`. |
| `mneva status`     | Print store path, indexer mode, and record count.                      |
| `mneva forget`     | Delete a record by id. Requires `--confirm`.                           |
| `mneva replay`     | Emit a tool-specific context block. `--tool` is required.              |
| `mneva serve`      | Start the localhost HTTP API on port 7432 (override with `--port`).    |
| `mneva synthesize` | Two-stage LLM idea pass over a scope (see Advanced below).             |
| `mneva digest`     | Consolidate a scope into a bootstrap document (see Advanced below).    |

Run `mneva <command> --help` for full flag listings.

## Advanced: LLM features (optional)

`synthesize` and `digest` call out to an LLM. They require an API key for
one of four supported backends:

- **Anthropic** — `ANTHROPIC_API_KEY` (default; model `claude-opus-4-7`)
- **OpenAI** — `OPENAI_API_KEY` (model `gpt-5`)
- **Google** — `GOOGLE_API_KEY` (model `gemini-2.0-pro`)
- **OpenRouter** — `OPENROUTER_API_KEY` (routes to any vendor model id)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
mneva synthesize --scope my-project
```

Keys are read from the environment at call time and never written to disk
or captured records. Override the model for any backend with
`MNEVA_<PROVIDER>_MODEL=<model-id>`. Full matrix and troubleshooting:
[`docs/providers.md`](./docs/providers.md).

## Design principles

- **Explicit** — context is visible, inspectable, editable
- **Yours** — data lives on your machine in plain markdown
- **File over app** — open format, no lock-in
- **BYOAI** — bring your own AI keys, choose your own models

## Status

Alpha (v0.1.0). The CLI, store, index, replay templates, and HTTP API are
working. Known gaps:

- No MCP server (planned for v1)
- No cloud sync (planned for v2; opt-in)
- No auto-distillation of long scopes (planned for v1)
- Single-user only

Real-key smoke is currently Anthropic-only. OpenAI, Google, and OpenRouter
backends pass mocked tests but have not been exercised against live
endpoints in this release. Issues and bug reports:
https://github.com/mneva-ai/mneva/issues.

## License and links

- License: [Apache 2.0](./LICENSE)
- Repository: https://github.com/mneva-ai/mneva
- Website: https://mneva.org
- Changelog: [`CHANGELOG.md`](./CHANGELOG.md)
