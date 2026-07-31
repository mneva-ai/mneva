# Changelog

## [Unreleased]

### Changed
- **Migrated off the end-of-life Google SDK.** `google-generativeai` reached EOL
  upstream ("All support for the `google.generativeai` package has ended") and
  emitted a `FutureWarning` on every import. The Google provider now uses the
  current `google-genai` SDK: `genai.Client(api_key=...)` plus
  `client.models.generate_content(model=..., contents=..., config=types.GenerateContentConfig(...))`,
  replacing the removed `genai.configure()` / `genai.GenerativeModel()` API.
  The default model, the `MNEVA_GOOGLE_MODEL` override, and the
  `complete(prompt, *, max_tokens) -> str` contract are all unchanged. The new
  SDK types `response.text` as `str | None`, so an empty response now normalizes
  to `""` rather than propagating `None` — covered by a new test.
- **Package description** now leads with the user-facing problem instead of
  internal architecture vocabulary.

### Changed (strategy)
- **Repositioned around Markdown ownership.** New positioning: *your AI memory is
  your own Markdown files — follows the repo, lives in git, opens in Obsidian, no
  account, no cloud.* This reverses the 2026-05-25 decision to target
  non-technical users first. The reversal followed a competitive analysis of
  `MemTensor/memmy-agent`, which had already shipped a stronger version of that
  plan (desktop app, free credits, one-click install, automatic history import).
  mneva's remaining differentiators all matter specifically to developers,
  Obsidian users, and privacy-sensitive users. Full reasoning is recorded in
  `.claude/claude-progress.txt`; this is a positioning change, not a claim that
  non-technical demand was disproven. Updated `CLAUDE.md`,
  `.claude/feature_list.json`, both READMEs, and the package description.

### Added
- **`mneva reindex`** — rebuilds the search index from the Markdown store. Use it
  after editing records by hand, restoring files, or upgrading. The Markdown
  files are the source of truth; the index is disposable.

### Fixed
- **New index columns were silently dropped on existing databases.**
  `Indexer._init_schema()` used `CREATE TABLE IF NOT EXISTS` with no version
  check, so any schema change was a no-op against a database that already
  existed — the table kept its old shape forever, and there was no `ALTER
  TABLE`, rebuild, or migration path anywhere in the codebase. The index now
  carries a schema version (`PRAGMA user_version`); on open, a database at an
  older version is rebuilt from the Markdown store. This also makes the
  documented invariant "SQLite is a rebuildable index" true in code, where it
  previously was not.

### Added
- **Project harness** — `CLAUDE.md`, `.claude/feature_list.json`, and
  `.claude/claude-progress.txt`. Records the architecture rules, the current
  strategy and its guardrail, the prioritized queue, and an append-only progress
  log, so picking the project back up does not require re-exploring it.
- **User research committed to version control.** Three research documents from
  2026-05-25 (118KB, including the strategic decision record) had been sitting
  untracked in the working tree.

## [0.2.2] - 2026-05-24

### Fixed
- **MCP config in the README did not work as written.** Every per-client config
  block used `"command": "uvx", "args": ["mneva-mcp"]`, i.e. `uvx mneva-mcp`,
  which fails with `mneva-mcp was not found in the package registry` — `uvx`
  resolves its argument as a *package* name, and `mneva-mcp` is a console script
  inside the `mneva` package, not a package. Corrected all blocks (Claude
  Desktop, Claude Code, Cursor, Windsurf, ChatGPT Desktop) to
  `"args": ["--from", "mneva", "mneva-mcp"]` in both the English and Chinese
  READMEs. Verified end-to-end against the published PyPI artifact. Added a
  first-launch note (cold start downloads deps once, then caches). No code
  change — the `mneva-mcp` entry point itself was always correct.

### Added
- **`mneva upgrade`** — one command to update mneva to the latest published
  version. Detects how the running interpreter was installed (pipx, `uv tool`,
  `uvx`, or plain `pip`) from `sys.prefix` and runs the matching upgrade
  command, so users don't have to remember which installer they used. `--dry-run`
  prints the detected command without running it. For an ephemeral `uvx` run it
  reports that nothing needs upgrading (uvx always fetches the latest).

### Fixed
- **`mneva --version` reported the wrong version.** The version was duplicated
  in `pyproject.toml` and `src/mneva/__init__.py`; the latter was not bumped at
  0.2.0 release, so `mneva --version` and `mneva diagnose` printed `0.1.3`.
  Version is now sourced solely from `src/mneva/__init__.py` via Hatchling's
  dynamic version (`[tool.hatch.version]`), eliminating the drift permanently.

## [0.2.0] - 2026-05-22

### Added
- **MCP server (`mneva-mcp`)** — mneva now speaks Model Context Protocol so any
  MCP-capable AI client (Claude Desktop, Claude Code, Cursor, Windsurf, Cline,
  Continue, ChatGPT Desktop in Developer Mode) reads and writes mneva memories
  natively. No API key required for the memory layer — the AI client supplies
  the intelligence; mneva supplies the cross-session, cross-tool persistence.
  - New module `mneva.mcp_server` using the official `mcp>=1.10,<2` SDK
    (FastMCP decorator API).
  - Six tools: `capture_memory`, `search_memory`, `forget_memory`,
    `list_recent_memories`, `replay_context`, `get_status`.
  - Each tool returns a dict with a human-readable `summary` field so the AI
    client can speak "I remembered that" instead of returning silent ids.
  - New console script `mneva-mcp` (entry point `mneva.mcp_server:main`).
  - Auto-init on first run: missing `~/.mneva/` materializes via
    `ensure_home()` + `load_or_init_config()` so users do not have to run
    `mneva init` before wiring the MCP server.
  - Startup failures (`OSError` on filesystem operations) write a structured
    line to `stderr` and exit with code 2 so MCP hosts can surface a
    diagnosable error.
  - Client attribution via the `MNEVA_MCP_CLIENT` env var declared in each
    client's MCP config block. Each tool call appends to
    `~/.mneva/.mcp-attribution.log` (1 MB cap, monthly rotation; counts only,
    zero record content).
- **`mneva diagnose [--share]`** — opt-in, user-initiated observability
  command. Prints a sanitized report (platform, Python version, mneva home
  state, sqlite-vec mode, record counts by lifespan, configured backends,
  per-client MCP attribution counts, last capture timestamp). The `--share`
  flag controls verbosity; output stays on stdout, the user copies manually.
  Zero passive collection — README's "no telemetry" promise stands.
- **`uvx mneva-mcp` (and `uvx mneva`) install path** — README headline switches
  to `uvx` for zero-install ad-hoc runs. `pipx` remains supported.
- **WAL journal mode on the SQLite index** — `Indexer.__init__` now opens the
  connection with `timeout=5.0` and immediately enables
  `PRAGMA journal_mode=WAL`, `busy_timeout=5000`,
  `synchronous=NORMAL`. Enables multiple `mneva-mcp` processes (one per AI
  client) to read and write the same store concurrently without
  `database is locked` errors. Existing v0.1.x databases auto-upgrade on first
  open; no migration needed.
- **`Record.to_dict()`** — single-source dataclass-to-dict helper used by the
  MCP server tools (and reusable by the HTTP API surface later). Replaces
  ad-hoc field-by-field serialization that would have duplicated 6 times
  across the MCP tools.
- Test additions:
  - `tests/unit/test_mcp_server.py` — per-tool happy + edge + error coverage,
    plus three IRON regression cases (auto-init on first run, env-var
    attribution, `Record.to_dict` round-trip stability).
  - `tests/unit/test_diagnose.py` — diagnose output + `--share` verbosity +
    zero-record-content sanity check.
  - `tests/integration/test_mcp_protocol.py` — `mcp.client.stdio.stdio_client`
    round-trip (`initialize` → `tools/list` → `tools/call`).
  - `tests/integration/test_concurrent_capture.py` — two-subprocess
    concurrent capture + WAL-upgrade-from-legacy-DB regression.

### Changed
- README rewritten: `uvx mneva-mcp` headline + per-client MCP config snippets
  (Claude Desktop, Claude Code, Cursor, Windsurf, ChatGPT Desktop, Cline,
  Continue). BYOK features (`synthesize` / `digest` / `distill`) moved to an
  "Advanced — BYOK features" section below the AI-agent wiring.
- README adds a "Using mneva from a browser chat UI" subsection documenting
  the v0.2 limitation (browser-only AIs cannot speak MCP) and the manual CLI
  workaround until v0.3 ships a browser extension.
- `pyproject.toml`: `mcp>=1.10,<2` dependency, `mneva-mcp` console script,
  classifiers extended to Python 3.13 and 3.14, `Homepage` switched from the
  parked `mneva.org` placeholder to the GitHub repo URL.
- `install-verify.yml` matrix extended with a `uvx --from . mneva-mcp` cell
  driving the SDK's `stdio_client` for a `tools/list` smoke check.

### Notes
- v0.1.x (pipx-based) install path remains supported. Existing users running
  `pipx upgrade mneva` get both `mneva` and `mneva-mcp` console scripts.
- `synthesize` / `digest` / `distill` (BYOK LLM features) intentionally NOT
  exposed via MCP — they require provider keys + slow LLM calls and would
  break the "instant local memory" MCP value proposition. They remain
  CLI-only Advanced features.
- v0.3 roadmap: browser extension for chat.openai.com / claude.ai /
  gemini.google.com / chat.deepseek.com via Manifest V3 + Chrome Native
  Messaging. Entry condition: v0.2 reaches ≥10 real users (verified via
  `mneva diagnose --share` reports) AND ≥3 request browser-UI support.
- v1+ roadmap: GUI installer for non-technical users + potential hosted
  `mneva.app` SaaS. Both gated on validated demand from technical users
  first; see `D:/AI/specs/mneva-v0.2-plan.md`-equivalent plan file.
- Multi-user feedback after v0.1.x ship surfaced two friction blockers —
  BYOK and `pipx` install — which drove the v0.2 product-form pivot from
  "CLI users operate directly" to "AI clients read/write mneva via MCP".

## [0.1.3] - 2026-05-17

### Fixed
- `mneva synthesize` / `digest` / `distill` now catch `MissingAPIKeyError`
  from `get_provider(...)` and surface it as a friendly `ClickException`
  rather than a raw stack trace. Previously, running any LLM-backed command
  without the corresponding `<PROVIDER>_API_KEY` env var produced a
  `Traceback` ending in `MissingAPIKeyError`. Now produces:
  `Error: missing API key for openrouter: set OPENROUTER_API_KEY in your environment`.

### Added
- **`mneva distill --source <transcript> --scope <name>`** — extract permanent
  records from a raw conversation transcript via the configured LLM provider.
  Closes the second ICP gap from interview #002 (geliming):
  > "几百条会话…我没办法提取出真正有价值的信息"
  - Supported transcript formats: `.md`, `.txt`, `.json` (Claude Code session
    shape `{messages: [...]}` is auto-detected; other JSON shapes pass
    through as raw dump).
  - Long transcripts are chunked at 80,000 chars (safe for 200k-context
    Anthropic with a 4k response budget); each chunk = one LLM call.
  - Cost-estimate gate: above ~$0.10 estimated the CLI prompts for
    confirmation; `--yes` bypasses for scripted use. OpenRouter backend
    skips the gate (pricing unknown).
  - Content-hash dedup across chunks within one run.
  - Records flow to `~/.mneva/store/` AND to the configured vault (if PR #9's
    vault is set up) via the existing `_mirror_to_vault_if_configured`
    helper.
  - `--backend` overrides the default provider (same pattern as
    `synthesize` / `digest`).
- New module `mneva.distill` with `parse_transcript`, `chunk_text`,
  `_parse_response`, `distill` orchestrator, `DistillResult`, `estimate_cost_usd`.
- 16 new tests:
  - `tests/unit/test_distill.py` (12) — parse formats, chunk boundaries,
    response parse incl. fence tolerance, malformed JSON → `ProviderError`,
    orchestrator end-to-end with mocked provider, cost estimate.
  - `tests/integration/test_cli_distill.py` (4) — happy path, empty refuse,
    cost-gate trigger, `--yes` bypass.

### Notes
- v0.1.x ICP-gap closure complete. The PR sequence #8 (gap fixes) → #9
  (Obsidian) → #10 (distill) closes both cherry-picks accepted in the
  2026-05-16 CEO review.
- Out of scope (TODOS for v0.1.4 / v0.2):
  - `.zip` ChatGPT export support
  - Eval suite for distill prompt golden tests
  - `--prompt` flag for custom extraction prompts
  - Source-hash fingerprint persistence for cross-run idempotency
  - README "Distill" section (doc-polish PR)

## [0.1.2] - 2026-05-17

### Added
- **Obsidian vault read-write integration**. Every capture can mirror into your
  Obsidian vault as a normal markdown note; round-trip edits flow back via
  `mneva sync-vault`.
  - New module `mneva.vault` with `detect_vault`, `write_to_vault`,
    `sync_from_vault`, `VaultError`. A directory only qualifies as a vault if
    it contains a `.obsidian/` subdirectory, so `mneva config set-vault`
    refuses arbitrary paths.
  - Records land at `<vault>/mneva/<scope>/<record_id>.md` with YAML
    frontmatter (`mneva_id`, `scope`, `lifespan`, `tool`, `source`).
  - New CLI subcommands:
    - `mneva config set-vault <path>` — validates `.obsidian/` + persists.
    - `mneva config get-vault` — prints current path.
    - `mneva config unset-vault` — clears the configured path.
    - `mneva sync-vault` — imports vault notes carrying `mneva_id` back into
      `~/.mneva/store/` (notes without `mneva_id` are skipped, so your
      hand-written Obsidian notes are never touched).
  - `mneva capture` now also writes to the vault when configured. Vault
    write failures (missing `.obsidian/`, permissions, iCloud lock) log a
    warning to stderr but do not fail the capture.
- `Config.vault_path: str | None = None` field; defaults to None so existing
  v0.1.1 configs load unchanged.
- 10 new tests: `tests/unit/test_vault.py` (8 cases for the vault module),
  `tests/integration/test_cli_vault.py` (7 cases for the CLI flow).

### Notes
- Targets the geliming-shaped "Obsidian-centric mid-user" ICP from interview
  #002. Closes one of the two scope gaps surfaced in CEO review
  (`mneva-v0.1-ceo-review-2026-05-16.md`).
- v0.1.3 (`mneva distill`) is queued next.

## [0.1.1] - 2026-05-17

### Fixed
- **Record collision rescue**: `cli capture` and `POST /capture` now catch
  `FileExistsError` from `write_record` and surface a friendly message
  (CLI: `ClickException`; HTTP: 409 Conflict). Previously the raw exception
  reached the user as a stack trace. Collisions are time-keyed and remain
  practically impossible; this is defense in depth.
- **Friendly config errors**: new `ConfigError` class. `load_config` now
  reports clear messages for missing config (`mneva config not found at <path>;
  run \`mneva init\` first`), malformed JSON (line + column), and
  schema-drift (`unexpected or missing fields`). Previously these raised raw
  `FileNotFoundError` / `JSONDecodeError` / `TypeError` with stack traces.
- **OpenAI / OpenRouter `None`-return handling**: both providers now raise
  `ProviderError` with model + `finish_reason` context when the SDK returns
  `content=None` (length-cap, refusal, or unexpected tool-use). Previously the
  function returned `None` typed as `str`, crashing downstream callers with an
  obscure `AttributeError`.

### Changed
- `_new_id` helper consolidated into `mneva.store.make_record_id` (was
  duplicated in `cli.py` and `api.py`). DRY hygiene; behavior unchanged.
- `Indexer` now derives its `home` path from the SQLite db path's parent,
  removing a stale `mneva_home()` call in `search()` that bypassed
  dependency injection.
- HTTP API token comparison uses `secrets.compare_digest` instead of `!=`
  (defense in depth for the localhost-only API).
- `paths._SUBDIRS` trimmed from `("store", "index", "adr", "templates")` to
  `("store",)` — the other three were never used.
- Dependency pins loosened from exact to ranges to avoid forcing
  downgrades of co-installed tools:
  - `anthropic==0.42.0` → `anthropic>=0.42.0,<1`
  - `openai==1.58.0` → `openai>=1.58.0,<3`
  - `google-generativeai==0.8.3` → `google-generativeai>=0.8.3,<1`

### Added
- Regression tests for all three CRITICAL GAPS above.
- `install-verify.yml` matrix expanded to Python 3.13 + 3.14 (forward-defense
  for upcoming Python releases).

### Notes
- Source-of-truth references for the change set: `D:/AI/specs/mneva-v0.1-ceo-review-2026-05-16.md`
  (CEO review) and `D:/AI/specs/mneva-v0.1-eng-review-2026-05-17.md` (Eng review).
- Next planned PRs: v0.1.2 (Obsidian read-write integration), v0.1.3 (`mneva distill`).

## [0.1.0] - 2026-05-10

### Added
- M0: project skeleton, dev deps, ruff/mypy/pytest configs, GitHub Actions CI matrix, tests scaffold with `tmp_mneva_home` fixture (tag `m0-skeleton`).
- M1: `paths.mneva_home`/`ensure_home` (env override + subdir creation) and `store.Record` + `write_record`/`read_record`/`forget_record`/`iter_records` with frontmatter persistence; coverage ≥ 90% on store.py.
- M2: `config.Config` dataclass + `generate_token` + 0600 save/load. `indexer.Indexer` with sqlite-vec mode probe and BM25 backbone (token-overlap pre-filter to handle small-corpus IDF edge cases); scope + lifespan filters; status reporting (tag `m2-indexer`).
- M3: `mneva` CLI commands — `init` (token + bootstrap, idempotent), `capture` (positional or stdin, sha256 id), `search` (scope + lifespan + -k filters), `status` (mode + count), `forget` (--confirm required). 32 tests pass, total coverage 94%.
- M4: FastAPI HTTP API on `localhost:7432` with `X-MNEVA-Token` middleware. Endpoints: `GET /status`, `POST /capture`, `POST /forget`, `GET /search`, `GET /replay`. `mneva serve` command with friendly port-collision detection. **Plan 1 Foundation complete** — 40 tests pass on Windows + coverage well above 80% gate (tags `m4-api`, `plan1-foundation`).
- M5: Provider abstraction with four backends (Anthropic, OpenAI, Google, OpenRouter). `mneva synthesize` two-stage pipeline — Stage 1 generates ~100 ideas / observations / patterns / connections / questions over a scope; Stage 2 runs a critical pass surfacing the most dangerous failure mode, invalidating assumption, and cross-cutting observation. BYOK via per-provider env var.
- M6: `mneva digest` produces a structured `bootstrap.md` synthesis artifact suitable for use as scope context in downstream tools. **Plan 2 Intelligence complete**.
- M7: Per-tool reference templates (`claude.md`, `cursor.md`, `chatgpt.md`, etc.) and `mneva replay --scope X --tool Y` emitting tool-specific bootstrap text via `GET /replay` (`PlainTextResponse`).
- M8: Integration tests covering replay templates, end-to-end CLI flows, and HTTP API error paths.
- M9: User-facing docs — `docs/alpha-onboarding.md` (install / init / synthesize / digest walkthrough) and `docs/providers.md` (BYOK setup per backend with model selection guidance).
- M10: CI matrix wheel install + smoke step (pre-publish gate) and `install-verify.yml` post-publish workflow auto-triggered by `release: published`, running `pipx install mneva==<version>` across the matrix.
- M11a: Release prep — version bump to 0.1.0, this CHANGELOG entry, real-PyPI publish, GitHub release tag.

### Fixed
- Windows: force UTF-8 stdout to prevent `cp1252` charmap crash on Unicode output (caught by alpha smoke testing).

### Notes
- BYOK — bring-your-own-key for any of four supported LLM providers (Anthropic, OpenAI, Google, OpenRouter). mneva never stores keys; pass via env var per provider.
- Multi-provider — switch backends via `--backend` flag on `synthesize` / `digest`; the same prompts work across providers.
- Local-first — all records, config, and index live under `MNEVA_HOME` (default `~/.mneva`) on the user's machine. No cloud component.
- No telemetry — mneva makes zero outbound network calls except those the user explicitly invokes (`synthesize` / `digest` to the chosen provider).

### Smoke coverage
Smoke-tested with a real key against the Anthropic backend (full Stage 1 + Stage 2 + `digest` pipeline). OpenAI, Google, and OpenRouter backends are covered by mocked tests only — please file an issue on real-key bugs for those backends.

### Known Limitations
- No MCP server (planned for v1).
- No cloud sync (planned for v2).
- No auto-distillation (planned for v1).
- Single-user only.

## [0.0.1] - 2026-05-02

Placeholder release to reserve the `mneva` name on PyPI. No functionality.
