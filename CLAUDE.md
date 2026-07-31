# CLAUDE.md — mneva

## Quick Orient

- **What**: local-first memory substrate. Markdown files are the source of truth; SQLite is a rebuildable index.
- **Stack**: Python ≥3.11, hatchling build, `click` CLI, `fastapi`+`uvicorn` HTTP API, official `mcp` SDK (FastMCP), `rank-bm25` + `sqlite-vec` retrieval, `python-frontmatter` storage.
- **Main branch**: `main`. Ship via PR (see `## Shipping`).
- **Version**: single source is `src/mneva/__init__.py` (`[tool.hatch.version]` reads it). **Never** put a version in `pyproject.toml` — that drift caused the 0.2.1 bug.
- **Entry points**: `mneva` → `mneva.cli:app`, `mneva-mcp` → `mneva.mcp_server:main`.

## Directory Map

| Path | Role |
|---|---|
| `src/mneva/cli.py` | All 14 CLI commands. Largest file — check here first for user-facing behavior. |
| `src/mneva/store.py` | `Record` dataclass + Markdown read/write. The storage contract. |
| `src/mneva/indexer.py` | BM25 + sqlite-vec index. **Rebuildable** — never the source of truth. |
| `src/mneva/mcp_server.py` | MCP server, 6 tools. Second-largest surface. |
| `src/mneva/api.py` | FastAPI HTTP layer (`mneva serve`). |
| `src/mneva/providers/` | 4 LLM backends (anthropic, openai, google, openrouter) behind `base.py`. |
| `src/mneva/vault.py` | Obsidian vault two-way sync. |
| `src/mneva/{synth,distill,replay}.py` | synthesize / distill / replay features. |
| `docs/*.json`, `docs/*.md` | **User research + the 2026-05-25 strategy decision.** Read before any product-direction work. |

## Session Startup Procedure

Read these three, in order, then start. **Do not pre-explore the codebase.**

1. This file (`CLAUDE.md`)
2. `.claude/feature_list.json` — the prioritized queue
3. Last 30 lines of `.claude/claude-progress.txt`

## Current Strategy — READ BEFORE PROPOSING PRODUCT WORK

**Decided 2026-07-31.** History: 5/25 chose a non-technical beachhead → **7/31 reversed** after the `MemTensor/memmy-agent` competitive analysis. Full reasoning in `.claude/claude-progress.txt`. Do not re-propose the non-technical line without reading that entry first.

**Positioning:**

> Your AI memory is your own Markdown files. It follows the repo, goes into git, opens in Obsidian, gets reviewed in a PR. No account, no cloud.

- **Target user**: developers who use more than one AI coding tool, Obsidian users, privacy-sensitive developers. Not non-technical users.
- **The five differentiators** (everything we build should sharpen at least one): Markdown is the source of truth; zero account / zero cloud; Obsidian two-way sync; deliberately scoped to the memory layer only; usable as a Python library.
- **Main line**: the engineer roadmap in `docs/user-research-hn-reddit-2026-05-25.md` §7–8 — git-aware metadata, stale/supersede, draft→review→promote, token-budgeted replay.
- **In user-facing copy, lead with**: Markdown, git-native, no account, reviewable, Obsidian, local. These were on the old avoid-list; that list is void.

**Why the reversal** (so it is not re-litigated): `memmy-agent` (created 2026-07-16, 355 stars in 15 days, MemTensor team) already shipped a better version of the non-technical plan — desktop app, free trial credits, one-click install, automatic history import from 6 agents, a four-layer memory engine. mneva's feature surface is a strict subset except Obsidian. All five differentiators above matter **only** to engineers, which is exactly who the 5/25 decision demoted. The reversal is not "non-technical demand was falsified" — that question still has zero evidence — it is that the competitive landscape made that line unwinnable while making this one defensible. memmy structurally cannot copy Markdown-as-truth: its four-layer engine requires a structured DB.

## Architecture Rules

1. **Markdown is the source of truth. SQLite is disposable.** Any change that makes the index authoritative, or that loses data when the index is deleted, is wrong. `iter_records()` reads from `~/.mneva/store/*.md`, never from SQLite.
2. **Always resolve paths through `paths.py`.** Use `mneva_home()` / `ensure_home()`; both honor `$MNEVA_HOME`. Never hardcode `~/.mneva` — the whole test suite depends on the override.
3. **`Record.to_dict()` is the single serialization point.** MCP tools and the HTTP API both go through it. Add a field there, not in each caller.
4. **Providers stay behind `providers/base.py`.** A provider only implements `complete(prompt, *, max_tokens) -> str`. No provider-specific logic leaks into `synth.py` / `distill.py`.
5. **MCP tools return a dict with a human-readable `summary` key**, so the AI client can say "I remembered that" rather than echoing an opaque id.
6. **No telemetry without an explicit user action.** `diagnose --share` is opt-in and user-initiated. Keep it that way.

## Health Stack

Used by gstack `/health`. Dead-code / shell / gbrain dimensions do not apply to this repo and correctly report SKIPPED.

- typecheck: `mypy src`
- lint: `ruff check .`
- test: `pytest`

## Adding a Feature

1. Confirm it is not excluded by `## Current Strategy` above.
2. Add an entry to `.claude/feature_list.json` with context + acceptance criteria.
3. Write the failing test first (`tests/unit/` for logic, `tests/integration/` for CLI/HTTP/MCP).
4. Implement.
5. `pytest` + `ruff check .` + `mypy src` all green.
6. Update `CHANGELOG.md` under `## [Unreleased]`.
7. Append to `.claude/claude-progress.txt`.

## Shipping

Bump `src/mneva/__init__.py`, update `CHANGELOG.md`, PR into `main`. CI (`.github/workflows/ci.yml`) plus `install-verify.yml` must be green. Releases are tagged `vX.Y.Z`.

## Common Mistakes to Avoid

1. **Duplicating the version into `pyproject.toml`.** Shipped a wrong `--version` for three releases. One source only: `src/mneva/__init__.py`.
2. **Documenting `uvx mneva-mcp`.** That fails — `uvx` resolves its argument as a *package*. The correct form is `uvx --from mneva mneva-mcp`. This shipped broken in the README once already.
3. **Truncating pytest output.** `pytest.ini` sets `-ra -q`, so the `N passed` line is the **last** line. Piping through `tail`/`grep` silently swallows it and makes a green run look empty.
4. **Treating the SQLite index as durable.** It is rebuilt from Markdown. Never write data that exists only in the index.
5. **Using `google.generativeai`.** EOL upstream; removed in `## [Unreleased]` (post-0.2.2). The provider now uses `google-genai` (`genai.Client(...)` → `client.models.generate_content(model=…, contents=…, config=types.GenerateContentConfig(…))`).
6. **Re-proposing the non-technical beachhead** (desktop app, landing page, Reddit outreach) as if 5/25 were still in force. It was reversed on 7/31 — see `## Current Strategy` and the progress log.
7. **Adding a column to `Indexer` and assuming it lands.** `_init_schema()` uses `CREATE TABLE IF NOT EXISTS`, so on an existing database a new column is a **silent no-op**. There is no `ALTER TABLE` and, as of this writing, no rebuild path. Any new indexed field needs a schema version + `rebuild()` from `store.iter_records()`.
8. **Post-filtering search results.** `Indexer.search()` filters in SQL *before* BM25 ranking. Filtering after retrieval breaks `top_k` — you ask for k and get fewer.

## Token Efficiency

- Read: this file, `.claude/feature_list.json`, tail of `.claude/claude-progress.txt`. That is enough to start.
- Do **not** read: `dist/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `.omc/`, the full `CHANGELOG.md` (18KB), or either README (30KB / 19KB) unless the task is specifically about release notes or docs.
- The `docs/*.json` research files are large (22–40KB). Query specific keys with a script; do not read them whole.
