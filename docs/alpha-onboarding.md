# Mneva Alpha Onboarding

Mneva is a local-first context substrate: a CLI that captures decisions, constraints, and state
into `~/.mneva/` and replays them on demand to any AI tool (Claude Code, Cursor, Codex).
This doc takes you from install to first replay in under five minutes — no API key required.

## Requirements

- Python 3.11+
- pipx installed (`pip install --user pipx` if not present)
- mneva v0.1.0 or later

## 1. Install

```bash
pipx install mneva
mneva --version
```

Alternative: `pip install --user mneva`

## 2. Initialize your store

```bash
mneva init
```

Your store lands at `~/.mneva/`. A unique token is printed once — stash it if you plan
to use the HTTP API (`mneva serve`) later.

## 3. Capture your first records

```bash
mneva capture --scope my-project --lifespan permanent \
    "decision: use SQLite over Postgres for v0 because zero-ops"

mneva capture --scope my-project --lifespan permanent \
    "constraint: no telemetry — alpha runs entirely offline-first"

mneva status
```

`mneva status` should report two records and show your store path and index mode.

## 4. Search

```bash
mneva search "SQLite"
```

Search uses BM25 full-text by default; if `sqlite-vec` is available it also runs vector search.

## 5. Replay into your AI tool

```bash
mneva replay --tool=claude-code --scope=my-project
```

This renders a context block ready to paste into your AI session. Paste it once, or — better —
wire the replay template into your tool's config so it auto-fetches every session.

### Wiring the template (one-time per project)

After install, mneva ships per-tool templates. Run `mneva replay --tool=<X>` to see the output,
then wire it as follows:

- **Claude Code**: paste the template content into your repo's `CLAUDE.md`
- **Cursor**: paste into `.cursor/rules/mneva.mdc` (the template includes the required YAML frontmatter)
- **Codex**: paste into repo-root `AGENTS.md`

After wiring, your AI tool will call `mneva replay` itself before responding — no manual paste needed.

## Next steps

- Run `mneva serve` to expose the HTTP API on `127.0.0.1:7432`
- Need `synthesize` or `digest`? See [docs/providers.md](./providers.md) for BYOK setup
  (Anthropic / OpenAI / Google / OpenRouter)
- Open issues at https://github.com/mneva-ai/mneva/issues

Built local-first. Your data stays on your machine.
