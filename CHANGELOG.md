# Changelog

## [Unreleased]

### Added
- M0: project skeleton, dev deps, ruff/mypy/pytest configs, GitHub Actions CI matrix, tests scaffold with `tmp_mneva_home` fixture (tag `m0-skeleton`).
- M1: `paths.mneva_home`/`ensure_home` (env override + subdir creation) and `store.Record` + `write_record`/`read_record`/`forget_record`/`iter_records` with frontmatter persistence; coverage ≥ 90% on store.py.
- M2: `config.Config` dataclass + `generate_token` + 0600 save/load. `indexer.Indexer` with sqlite-vec mode probe and BM25 backbone (token-overlap pre-filter to handle small-corpus IDF edge cases); scope + lifespan filters; status reporting (tag `m2-indexer`).
- M3: `mneva` CLI commands — `init` (token + bootstrap, idempotent), `capture` (positional or stdin, sha256 id), `search` (scope + lifespan + -k filters), `status` (mode + count), `forget` (--confirm required). 32 tests pass, total coverage 94%.
