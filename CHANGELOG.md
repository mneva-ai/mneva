# Changelog

## [Unreleased]

### Changed
- docs: rewrite `README.md` from v0.0.1 placeholder to alpha-ready content
  (install, quick start, tool-wiring, commands, BYOK matrix). Repo-visible
  immediately; PyPI page updates on next release.

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
