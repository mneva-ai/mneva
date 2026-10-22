# Changelog

## [Unreleased]

### Added
- `docs/format.md` describes the Markdown files mneva keeps (location,
  frontmatter fields, the profile, the Obsidian mirror, how another tool can
  read or write records), so other tools can use the same files without mneva.

### Changed
- README (English and Chinese) rewritten for people who use AI mainly in the
  browser: one-line install first, then the three setup steps, a table of what
  works where, and the developer material below. Removed the generated project
  index, the badge row and dead links; the roadmap now covers 0.5 to 0.7 and
  the next three releases.

## [0.7.0] - 2026-10-21

### Added
- **Install in one line, with no Python beforehand.** `install/install.ps1`
  (Windows) and `install/install.sh` (macOS, Linux) install uv, then
  `uv tool install mneva`, then run `mneva setup`, and put `mneva` on PATH for
  new terminals. With `MNEVA_MIRROR=cn` every download comes from mirrors
  reachable in mainland China (uv and packages from the Tsinghua PyPI mirror,
  or Tencent's when Tsinghua does not answer; Python from npmmirror); later
  `mneva upgrade` runs keep using the mirror. Both READMEs lead with the
  command. CI runs both scripts on clean machines for every PR.
- **`mneva setup` connects the Claude desktop app** by adding mneva to
  `claude_desktop_config.json`. Other servers and settings are kept, an
  existing entry is left alone, and a file that does not parse is never
  rewritten; setup prints the entry to add by hand instead.
- The native host's `ping` reply lists the message types it supports, so a
  store-updated extension can tell an older mneva apart and ask for
  `mneva upgrade`.
- `store/build.py` builds the Chrome Web Store and Edge Add-ons upload without
  the manifest `key`; `docs/privacy.md` is the extension's privacy policy.

### Changed
- `mneva setup`'s closing text names Chrome and Edge and all five sites.

## [0.6.0] - 2026-10-19

### Added
- **`mneva learn` now runs by itself about once a day.** mneva's MCP server
  starts with each Claude Code or Codex session; when the last run finished
  more than 20 hours ago and you have a profile, it starts one learn run in the
  background over your newest prompts (at least 20, at most about 120,000
  characters). It uses only your Claude Code login, never an API key. When
  edits are waiting, the next conversation's profile tells the AI to mention
  them in one line; nothing changes until you run `mneva learn --accept`.
  Set `MNEVA_LEARN_AUTO=0` to turn it off. The run logs to `~/.mneva/learn.log`.

## [0.5.0] - 2026-10-19

### Added
- **`mneva learn` keeps your profile current from your own AI history.** It
  reads the prompts you typed into Claude Code (`~/.claude/history.jsonl`) and
  Codex (session files), leaves out text the tools inject, pasted documents and
  obvious secrets, extracts dated facts about you, and proposes edits to your
  profile records. Nothing is written until you accept an edit; an edit keeps
  the record's id. Facts are extracted by your local Claude Code (`claude -p`,
  no API key for mneva, run with tools, MCP servers, plugins and session
  saving off); `--backend` picks an API provider instead. Later runs read only
  new prompts.

## [0.4.2] - 2026-10-17

### Changed
- **`mneva upgrade` is one step.** After updating the package it runs
  `mneva setup --after-upgrade` in a new process, so the new version refreshes
  the browser extension copy and the native host launcher. uvx users, who have
  nothing to update, still get the refresh.
- **The browser extension reloads itself after an upgrade** (extension 0.3.0).
  The native host now reports the version of the extension copy in the data
  root; when it differs from the running version, the extension reloads once
  (at most once per version, so a copy loaded from another folder cannot loop)
  and puts its content script back into AI tabs that are already open. This
  adds `host_permissions` for exactly the five sites the content script
  already runs on. Extensions loaded before this release still need one manual
  reload click.

## [0.4.1] - 2026-10-17

### Added
- **Grok in the browser extension.** New chats on grok.com start with your
  profile too, and Grok has its own switch in the popup. Grok first renders a
  plain textarea and swaps in a ProseMirror editor once the app loads; the
  adapter matches both and the post-insert recheck covers the swap. Checked
  on the live site on 2026-10-17.

## [0.4.0] - 2026-10-16

### Added
- **Browser extension: new web chats start with your profile.** A Manifest V3
  extension (Chrome, Edge) ships inside the package at `mneva/extension/`.
  When you open a new conversation on chatgpt.com, claude.ai,
  gemini.google.com or doubao.com and the composer is empty, it inserts your
  current profile brief; you type your question underneath. It never touches a
  composer that already has text or an existing conversation, follows
  single-page "New chat" navigation, and can be switched off per site in its
  popup. Alt+Shift+M inserts the profile into the focused field on any other
  site. Selectors for ChatGPT, Claude and Gemini were checked on the live sites
  on 2026-10-16; Doubao falls back to the largest visible text field and is
  unverified.
- **Native messaging host (`mneva-native-host`).** The extension reads the
  brief through Chrome native messaging, so there is no server to run, no
  token, and nothing leaves the machine. The host answers only `ping` and
  `get_brief`, never writes, uses binary stdio (Windows text mode would corrupt
  the length prefix), and rejects malformed or oversized frames.
- **`mneva setup` registers the host** for Chrome, Edge and Chromium (Windows
  registry under HKCU; manifest directories on macOS and Linux, only for
  browsers that are installed). It copies the extension to
  `~/.mneva/extension/` and prints that folder for "Load unpacked": the package
  folder would break, since uvx runs from a cache that gets pruned and upgrades
  replace files under a loaded extension. When an upgrade changes the copy,
  setup says to click reload on the extension card. Idempotent; `--dry-run`
  writes nothing. A failure here is reported
  and does not stop the agent registrations.

## [0.3.3] - 2026-10-16

### Changed
- **Stale-copy reminders need no tool name.** `mneva brief --copy` now
  records every copy by itself, one entry per budget, so a 1500-char copy for
  ChatGPT and a full copy elsewhere are both tracked with no extra input. The
  `--for` option added in 0.3.2 is removed: asking users to name each tool was
  friction the reminder existed to avoid. The reminder now says the profile
  changed since the last copy and prints the exact command(s) to copy again.
  Printing without `--copy` is not tracked.

## [0.3.2] - 2026-10-16

### Added
- **Reminders when a pasted profile goes stale.** `mneva brief --for <tool>`
  (e.g. `--for chatgpt`) records which brief that tool received and with
  which budget; later runs for the same tool reuse the budget, so
  `--max-chars 1500` only has to be typed once. When the profile changes,
  the tools now holding an old copy are named in three places: the reply to
  an MCP `capture_memory` with scope `profile` (where profile edits usually
  happen), `mneva status`, and every `mneva brief` run. Only a change to the
  text a tool actually received counts: editing a record that never fit that
  tool's budget does not. The bookkeeping lives in
  `~/.mneva/brief-copies.json`; deleting it loses only the reminders.

## [0.3.1] - 2026-10-16

### Added
- **Agents read your profile without being asked.** The MCP server now sends
  instructions at initialize: once per conversation, before the first
  substantive answer, call `replay_context` with `scope="profile"`, and call
  `capture_memory` only when the user asks. Clients such as Claude Code put
  server instructions in the model's context, so the per-session "read my
  mneva profile" step goes away. `mneva setup` no longer suggests editing
  `~/.claude/CLAUDE.md` for this.

## [0.3.0] - 2026-10-16

### Added
- **`mneva setup`: one command after install.** Registers mneva's MCP server
  with every agent CLI it finds on PATH (Claude Code at user scope, Codex),
  through each client's own `mcp add` command, with `MNEVA_MCP_CLIENT` set so
  memories record which agent wrote them. It also writes
  `~/.mneva/profile-template.md` and prints the next steps. Re-running changes
  nothing: a client that already has an `mneva` server is left alone, and an
  existing template is never overwritten. `--dry-run` prints the commands
  without running them. A uvx run registers `uvx --from mneva mneva-mcp`;
  every other install registers the running interpreter with
  `-m mneva.mcp_server`, which works even when `mneva-mcp` is not on the
  agent's PATH. A client whose registration fails is reported and does not
  stop the others.
- **`mneva brief`: a paste-ready profile for tools without MCP.** Records with
  scope `profile` and lifespan `permanent` form your personal profile; `brief`
  packs them into a character budget (`--max-chars`, default 4000; use 1500
  for ChatGPT custom instructions) for Doubao, Gemini, a video tool's prompt
  box, or anything else you paste into. Whole records only: a record that
  does not fit is skipped and named, never cut mid-sentence. The profile
  ignores `repo`, so it travels to every tool. `--copy` puts it on the
  clipboard; on Windows this writes through the Win32 API, because `clip.exe`
  either keeps a BOM as a visible character or misreads short Chinese text.
- **Git-aware memories.** Capturing inside a repository now records where the
  memory came from: `repo`, `repo_path`, `branch`, and `commit_sha` land in the
  note's YAML frontmatter, so a memory carries its project, branch, and the
  exact code state it was written against. `mneva search` scopes results to the
  current repository by default; `--all-repos` widens it and `--repo <id>`
  targets another one. `mneva capture --no-git` opts out entirely, since
  `repo_path` reveals local directory layout.
  - `repo` is derived from the remote URL and normalized
    (`git@github.com:Org/Repo.git`, `https://github.com/org/repo`, and
    `ssh://git@github.com/org/repo.git` all become `github.com/org/repo`), so
    it keeps matching after the repository is cloned to another machine or
    directory. Repositories with no remote fall back to `local:<dirname>`.
  - **Memories with no repository stay visible everywhere.** Filtering is
    `repo = ? OR repo IS NULL`, never a bare equality: everything captured
    before this release, and anything captured outside a repository, would
    otherwise vanish from default search.
  - Git detection never fails a capture. A missing `git` binary, a directory
    that is not a repository, a repository with no commits, a detached HEAD, or
    a hanging `git` call all degrade to "no provenance" instead of an error.
  - **MCP clients must pass `repo_path`.** `capture_memory`, `search_memory`,
    and `replay_context` take an optional `repo_path`. The MCP server runs as
    its own process and inherits the AI client's working directory, not the
    user's project, so it cannot detect the repository by itself. The tool
    descriptions instruct the client to pass the workspace root.
  - `mneva status` now reports provenance coverage (`with repo provenance: N /
    M`) and the current repository. Without it, an AI client that never passes
    `repo_path` looks identical to one that does.

### Changed
- **Record frontmatter now has a single reader and writer.** `store.py` and
  `vault.py` each kept their own hardcoded field list, so a new field had to be
  added in three places and any miss silently dropped data — the vault round
  trip (`capture` → Obsidian → `sync-vault`) would have erased git provenance
  from the canonical record. Both directions now go through
  `store.record_frontmatter` / `store.record_from_frontmatter`.
- Optional fields are omitted from frontmatter rather than written as `null`,
  keeping notes readable in Obsidian.
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
- **`mneva capture -` crashed on Chinese input on Windows.** stdin was decoded
  in the console code page, turning a UTF-8 file into lone surrogates. stdin
  is now read as UTF-8 (a BOM is accepted); input that is not UTF-8 is refused
  with a clear message instead of being stored as garbage.
- **New index columns were silently dropped on existing databases.**
  `Indexer._init_schema()` used `CREATE TABLE IF NOT EXISTS` with no version
  check, so any schema change was a no-op against a database that already
  existed — the table kept its old shape forever, and there was no `ALTER
  TABLE`, rebuild, or migration path anywhere in the codebase. The index now
  carries a schema version (`PRAGMA user_version`); on open, a database at an
  older version is rebuilt from the Markdown store. This also makes the
  documented invariant "SQLite is a rebuildable index" true in code, where it
  previously was not. Note: because every existing database predates the
  version stamp, the **first** open after upgrading does a full rescan of
  `~/.mneva/store/`. It is synchronous, so a large store makes that one launch
  slower; subsequent opens skip it.
- **Concurrent startup could fail with "database is locked".**
  `PRAGMA journal_mode=WAL` ran *before* `busy_timeout` was configured, and
  SQLite returns `SQLITE_BUSY` for a journal-mode conversion without invoking
  the busy handler — so two `mneva-mcp` processes (one per AI client) opening a
  fresh or pre-WAL database at the same moment could race, and one would error
  out instead of waiting. `busy_timeout` is now set first, and the WAL switch
  is best-effort: losing that race is harmless, since the winner sets the same
  mode on the same file and the mode persists on disk.

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
