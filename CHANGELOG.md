# Changelog

## [Unreleased]

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
