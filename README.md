<div id="top">

<!-- HEADER STYLE: MODERN -->
<div align="left" style="position: relative; width: 100%; height: 100%; ">

# MNEVA

<em>AI coding memory as plain Markdown. Follows your repo, lives in git, opens in Obsidian. No account, no cloud.</em>

<!-- BADGES -->
<!-- local repository, no metadata badges. -->

<em>Built with the tools and technologies:</em>

<img src="https://img.shields.io/badge/Anthropic-191919.svg?style=flat-square&logo=Anthropic&logoColor=white" alt="Anthropic">
<img src="https://img.shields.io/badge/TOML-9C4121.svg?style=flat-square&logo=TOML&logoColor=white" alt="TOML">
<img src="https://img.shields.io/badge/Ruff-D7FF64.svg?style=flat-square&logo=Ruff&logoColor=black" alt="Ruff">
<img src="https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square&logo=FastAPI&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Pytest-0A9EDC.svg?style=flat-square&logo=Pytest&logoColor=white" alt="Pytest">
<br>
<img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat-square&logo=Python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/GitHub%20Actions-2088FF.svg?style=flat-square&logo=GitHub-Actions&logoColor=white" alt="GitHub%20Actions">
<img src="https://img.shields.io/badge/OpenAI-412991.svg?style=flat-square&logo=OpenAI&logoColor=white" alt="OpenAI">
<img src="https://img.shields.io/badge/Google%20Gemini-8E75B2.svg?style=flat-square&logo=Google-Gemini&logoColor=white" alt="Google%20Gemini">

</div>
</div>
<br clear="right">

**English** | [中文](./README.zh-CN.md)

---

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [What you get](#what-you-get)
- [Project Structure](#project-structure)
    - [Project Index](#project-index)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Usage](#usage)
    - [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

**Every AI memory tool keeps your memory in its own database. mneva keeps it in your files.**

Records are plain Markdown with YAML frontmatter under `~/.mneva/store/`. You can read them, `grep` them, edit them in any editor, commit them to git, and open them in Obsidian. The SQLite index is disposable — delete it and it rebuilds from the Markdown. No account to create, no cloud to sync to, no telemetry on by default.

**The problem it solves:** every AI assistant forgets. Open a new chat and you re-explain your project from scratch. Switch from Claude Code to Cursor and the context doesn't follow. Capture a decision once; every MCP-capable tool can read it.

**Why that matters more than the storage engine:** a memory you can't read is a memory you can't audit, correct, or trust. When your assistant records something wrong about your architecture, you want to open the file and fix the line — not query an opaque store and hope.

**v0.2 — mneva now speaks MCP.** Wire `mneva-mcp` into any Model Context Protocol client (Claude Desktop, Claude Code, Cursor, Windsurf, Cline, Continue, ChatGPT Desktop in Developer Mode) in 30 seconds. The AI client supplies the intelligence; mneva supplies the memory. No API key required for the memory layer.

---

## What you get

- **🧠 Memory that crosses tools.** Capture a fact in one AI client, recall it in another. Your context stops dying inside a single chat window.
- **⚡ Zero-key, 30-second setup.** The MCP memory layer needs no API key — your AI client already supplies the intelligence. One config block, restart, done.
- **🏠 Your data, on your disk.** Records are plain `.md` files under `~/.mneva/`. Read them in any editor, sync them through your own Obsidian vault, version them with git. No server, no account, no upload.
- **🔍 Search that finds the right memory.** BM25 keyword ranking with optional `sqlite-vec` vector reranking, filtered by project scope and by how long a memory should live (transient vs permanent).
- **🔒 Private by default.** mneva makes zero outbound network calls unless you opt into the advanced BYOK features. No telemetry, ever — the opt-in `mneva diagnose --share` is the only thing that emits anything, and it goes to your clipboard, not to us.

### Before / after

**Without mneva**, every new session starts the same way:

> "Quick context: we're on SQLite not Postgres, auth lives in `auth.ts`, and we already ruled out websockets…"

**With mneva**, you said it once. Any AI client you wire up just knows — across chats, across tools, across days.

### Under the hood

- **Python 3.11+**, one self-contained CLI (`mneva`) plus an MCP server (`mneva-mcp`).
- **MCP server** built on the official `mcp` SDK (FastMCP), exposing six tools your AI client auto-discovers: `capture_memory`, `search_memory`, `forget_memory`, `list_recent_memories`, `replay_context`, `get_status`.
- **Storage:** plain Markdown + YAML frontmatter under `~/.mneva/`, indexed by SQLite (WAL mode for safe concurrent access from multiple AI clients).
- **Search:** `rank-bm25` keyword scoring with optional `sqlite-vec` vector reranking.
- **Optional HTTP API** (`mneva serve`, FastAPI) and **BYOK providers** (Anthropic / OpenAI / Google / OpenRouter) power the advanced `synthesize` / `digest` / `distill` commands.

---

## Project Structure

```sh
└── mneva/
    ├── .github
    │   └── workflows
    ├── CHANGELOG.md
    ├── docs
    │   ├── alpha-onboarding.md
    │   ├── manual-smoke-m6.md
    │   └── providers.md
    ├── LICENSE
    ├── mypy.ini
    ├── pyproject.toml
    ├── pytest.ini
    ├── README.md
    ├── src
    │   └── mneva
    └── tests
        ├── __init__.py
        ├── __pycache__
        ├── conftest.py
        ├── integration
        └── unit
```

### Project Index

<details open>
	<summary><b><code>mneva/</code></b></summary>
	<!-- __root__ Submodule -->
	<details>
		<summary><b>__root__</b></summary>
		<blockquote>
			<div class='directory-path' style='padding: 8px 0; color: #666;'>
				<code><b>⦿ __root__</b></code>
			<table style='width: 100%; border-collapse: collapse;'>
			<thead>
				<tr style='background-color: #f8f9fa;'>
					<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
					<th style='text-align: left; padding: 8px;'>Summary</th>
				</tr>
			</thead>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/LICENSE'>LICENSE</a></b></td>
					<td style='padding: 8px;'>- Defines the legal terms for using, modifying, and distributing the project under the Apache License 2.0, granting copyright and patent permissions, outlining contribution submission, and disclaiming warranties<br>- This permissive license fosters open collaboration and community adoption while protecting both the copyright holder and users from liability<br>- It is the foundational governance for all project code.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/mypy.ini'>mypy.ini</a></b></td>
					<td style='padding: 8px;'>- Configures strict static type checking for the projects core source code, enforcing Python 3.11 standards and ensuring type consistency while gracefully handling third-party libraries with missing annotations<br>- Maintains code quality and reduces runtime errors across the architecture.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/pyproject.toml'>pyproject.toml</a></b></td>
					<td style='padding: 8px;'>- Configures the Mneva project as a Python package for a persistent agent context substrate and local-first CLI<br>- It declares dependencies for the server, CLI, LLM integrations, and search components<br>- It also sets up the CLI entry point and development tooling, ensuring proper packaging and distribution of the application.</td>
				</tr>
				<tr style='border-bottom: 1px solid #eee;'>
					<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/pytest.ini'>pytest.ini</a></b></td>
					<td style='padding: 8px;'>- Configures pytest’s test discovery in the <code>tests</code> directory, adds command-line flags for concise reporting, defines an <code>integration</code> marker for filesystem and HTTP end-to-end tests, and enables asyncio mode<br>- This standardizes how the project runs its unit and integration tests, ensuring consistent behavior across the codebase.</td>
				</tr>
			</table>
		</blockquote>
	</details>
	<!-- .github Submodule -->
	<details>
		<summary><b>.github</b></summary>
		<blockquote>
			<div class='directory-path' style='padding: 8px 0; color: #666;'>
				<code><b>⦿ .github</b></code>
			<!-- workflows Submodule -->
			<details>
				<summary><b>workflows</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ .github.workflows</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/.github/workflows/ci.yml'>ci.yml</a></b></td>
							<td style='padding: 8px;'>Automates continuous integration across multiple operating systems and Python versions, ensuring code quality through linting, type-checking, testing with coverage thresholds, and verifying the built wheel has no duplicate entries before installing and running a version smoke test.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/.github/workflows/install-verify.yml'>install-verify.yml</a></b></td>
							<td style='padding: 8px;'>- Automates post-release validation by installing the mneva package across multiple operating systems and Python versions using pipx, then confirming a successful installation with a version check<br>- This ensures the released package is functional and accessible, integral to the projects continuous integration and delivery pipeline.</td>
						</tr>
					</table>
				</blockquote>
			</details>
		</blockquote>
	</details>
	<!-- src Submodule -->
	<details>
		<summary><b>src</b></summary>
		<blockquote>
			<div class='directory-path' style='padding: 8px 0; color: #666;'>
				<code><b>⦿ src</b></code>
			<!-- mneva Submodule -->
			<details>
				<summary><b>mneva</b></summary>
				<blockquote>
					<div class='directory-path' style='padding: 8px 0; color: #666;'>
						<code><b>⦿ src.mneva</b></code>
					<table style='width: 100%; border-collapse: collapse;'>
					<thead>
						<tr style='background-color: #f8f9fa;'>
							<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
							<th style='text-align: left; padding: 8px;'>Summary</th>
						</tr>
					</thead>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/api.py'>api.py</a></b></td>
							<td style='padding: 8px;'>- Defines the FastAPI web application exposing endpoints for capturing, forgetting, searching, and replaying records<br>- Integrates authentication via token middleware, coordinates with the indexer for search, store for persistence, and replay module for output<br>- Provides the primary HTTP interface through which external tools interact with the Mneva knowledge base.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/cli.py'>cli.py</a></b></td>
							<td style='padding: 8px;'>- Defines the command-line interface for the mneva persistent agent context substrate using Click<br>- It exposes commands to initialize the data root, capture and search records, generate context replays for various AI coding tools, start a local API server, and perform two-stage synthesis or bootstrap digest consolidation<br>- This module acts as the primary user-facing entry point.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/config.py'>config.py</a></b></td>
							<td style='padding: 8px;'>- Manages application configuration by defining a frozen dataclass for settings like API token and embedding provider, and provides utilities to persist and load configuration from a JSON file<br>- This centralizes configuration handling, ensuring consistent access to runtime parameters across the entire codebase.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/indexer.py'>indexer.py</a></b></td>
							<td style='padding: 8px;'>- Implements a hybrid search index that combines BM25 ranking with optional sqlite-vec re-ranking for querying stored records<br>- Manages record insertion, deletion, and retrieval with filtering by scope and lifespan<br>- Supports both full-text and vector-powered search modes, returning the top-k relevant records for a given query.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/paths.py'>paths.py</a></b></td>
							<td style='padding: 8px;'>- Manages the applications home directory by respecting the $MNEVA_HOME environment variable or defaulting to ~/.mneva<br>- Ensures the root and required subdirectories (store, index, adr, templates) exist, creating them idempotently<br>- This foundational module enables consistent data storage and retrieval across the entire codebase.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/replay.py'>replay.py</a></b></td>
							<td style='padding: 8px;'>- Generates context replay blocks for supported tools by combining template bodies with captured permanent records, optionally filtered by scope<br>- Serves as shared logic used by both the mneva replay CLI command and the GET /replay HTTP endpoint, ensuring consistent output formatting across interfaces.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/store.py'>store.py</a></b></td>
							<td style='padding: 8px;'>- Persists and retrieves structured records as markdown files with frontmatter metadata, serving as the data access layer for the projects file-based store<br>- It handles serialization and provides create, read, update, delete, and iteration operations, abstracting file system details from the rest of the codebase.</td>
						</tr>
						<tr style='border-bottom: 1px solid #eee;'>
							<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src/mneva/synth.py'>synth.py</a></b></td>
							<td style='padding: 8px;'>- Implements a two-stage brainstorming and critical analysis pipeline using captured context records, along with a digest generator for producing L1 bootstrap summaries<br>- All large language model calls are routed through the Provider protocol, keeping the module provider-agnostic and enabling testable orchestration of the full workflow from context dump to final output.</td>
						</tr>
					</table>
					<!-- providers Submodule -->
					<details>
						<summary><b>providers</b></summary>
						<blockquote>
							<div class='directory-path' style='padding: 8px 0; color: #666;'>
								<code><b>⦿ src.mneva.providers</b></code>
							<table style='width: 100%; border-collapse: collapse;'>
							<thead>
								<tr style='background-color: #f8f9fa;'>
									<th style='width: 30%; text-align: left; padding: 8px;'>File Name</th>
									<th style='text-align: left; padding: 8px;'>Summary</th>
								</tr>
							</thead>
								<tr style='border-bottom: 1px solid #eee;'>
									<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src\mneva/providers/anthropic.py'>anthropic.py</a></b></td>
									<td style='padding: 8px;'>- Enables prompt-driven text completions through Anthropics API, using a default large-context model<br>- Handles authentication by checking for an API key in environment variables and raises an error if missing<br>- This provider supports the systems extensible architecture by abstracting Anthropic as one of multiple possible AI backends.</td>
								</tr>
								<tr style='border-bottom: 1px solid #eee;'>
									<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src\mneva/providers/base.py'>base.py</a></b></td>
									<td style='padding: 8px;'>- Defines the Provider protocol and error classes that form the foundation for all LLM adapter implementations<br>- Providers implement a one-shot non-streaming complete method, relying solely on environment variables for API keys<br>- MissingAPIKeyError enforces secure key management, while ProviderError serves as a catch-all for provider-side failures.</td>
								</tr>
								<tr style='border-bottom: 1px solid #eee;'>
									<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src\mneva/providers/google.py'>google.py</a></b></td>
									<td style='padding: 8px;'>- Configures the Google Generative AI provider as part of the provider abstraction layer, using Google's Gemini models<br>- It retrieves the API key from environment variables and exposes a completion interface for generating text responses, seamlessly integrating into the mneva ecosystem for multi-provider support.</td>
								</tr>
								<tr style='border-bottom: 1px solid #eee;'>
									<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src\mneva/providers/openai.py'>openai.py</a></b></td>
									<td style='padding: 8px;'>- Provides integration with OpenAI's GPT models as a provider for completions<br>- Handles API key authentication from environment variables and offers a simple interface to generate text responses<br>- This enables the mneva system to leverage OpenAIs large language models for various tasks.</td>
								</tr>
								<tr style='border-bottom: 1px solid #eee;'>
									<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src\mneva/providers/openrouter.py'>openrouter.py</a></b></td>
									<td style='padding: 8px;'>- Provides OpenRouter integration by wrapping the OpenAI client with a customized base URL and default model, enabling the application to use a wide range of LLMs through OpenRouters unified API<br>- The model is configurable via environment variable, and it validates the API key at initialization, raising a helpful error if missing<br>- Its role in the provider pattern ensures a consistent interface for completion tasks across different backends.</td>
								</tr>
							</table>
						</blockquote>
					</details>
				</blockquote>
			</details>
		</blockquote>
	</details>
</details>

---

## Getting Started

### Prerequisites

- **Python 3.11 or newer**
- **uv** (recommended). If you do not already have uv:
  - **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - **Windows (PowerShell):** `irm https://astral.sh/uv/install.ps1 | iex`
  - If `uv` is not recognized after install on Windows, close and reopen your terminal (uv writes itself to PATH at install time but the change is only picked up on a fresh shell — same gotcha pipx has).

`pipx` is still supported as a fallback; see *Alternative installs* below.

### Wire mneva into your AI agent (the headline path)

Pick the AI client you use most. Paste the snippet into its MCP config and restart the client. The first time mneva-mcp launches it creates `~/.mneva/` automatically — no `mneva init` required.

> **First launch is slow, then instant.** The first run downloads mneva and its dependencies (a few seconds) and caches them. If your client flags the server as slow or failed on the very first try, restart the client once — it connects from cache immediately. To pre-warm, run `uvx --from mneva mneva-mcp` once in a terminal and press Ctrl-C after it starts.

**Claude Desktop** — edit `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mneva": {
      "command": "uvx",
      "args": ["--from", "mneva", "mneva-mcp"],
      "env": { "MNEVA_MCP_CLIENT": "claude-desktop" }
    }
  }
}
```

**Claude Code** — edit `~/.claude.json` (or run `claude mcp add`):

```json
{
  "mcpServers": {
    "mneva": {
      "command": "uvx",
      "args": ["--from", "mneva", "mneva-mcp"],
      "env": { "MNEVA_MCP_CLIENT": "claude-code" }
    }
  }
}
```

**Cursor** — create `~/.cursor/mcp.json` (or `.cursor/mcp.json` in your workspace):

```json
{
  "mcpServers": {
    "mneva": {
      "command": "uvx",
      "args": ["--from", "mneva", "mneva-mcp"],
      "env": { "MNEVA_MCP_CLIENT": "cursor" }
    }
  }
}
```

**Windsurf** — edit `~/.codeium/windsurf/mcp_config.json` with the same shape (`"MNEVA_MCP_CLIENT": "windsurf"`).

**ChatGPT Desktop** — MCP support is currently behind **Developer Mode (beta)** in the in-app settings; enable it and add the same config block (`"MNEVA_MCP_CLIENT": "chatgpt-desktop"`).

**Cline / Continue** — both honor the same Manifest, scoped to your VS Code workspace.

After restart, ask the AI client *"remember that we decided X"* and watch mneva append a record. Search it next session.

### Try it from the command line

The CLI is the lower-level surface — useful for scripting and for use cases where you don't have an MCP client.

```sh
uvx mneva init
uvx mneva capture --scope my-project --lifespan permanent \
    "decision: use SQLite over Postgres for v0 because zero-ops"
uvx mneva search "SQLite"
uvx mneva replay --tool=claude-code --scope=my-project
```

Because the Markdown is the source of truth, you can edit `~/.mneva/store/*.md`
in any editor and then bring the index back in line:

```sh
uvx mneva reindex   # rebuild the search index from the Markdown files
```

The index is disposable — delete `~/.mneva/mneva.sqlite`, run `reindex`, and
nothing is lost.

### Using mneva from a browser chat UI

The MCP path covers desktop AI clients. Browser-only AI chat UIs (claude.ai web, chatgpt.com, gemini.google.com, chat.deepseek.com) cannot speak MCP because browsers do not allow web pages to spawn local processes. Until v0.3 ships a browser extension, the workaround is:

| Your AI                                | v0.2 native support              | Workaround                                              |
| -------------------------------------- | -------------------------------- | ------------------------------------------------------- |
| Claude Desktop / Claude Code           | ✅ MCP                            | —                                                       |
| Cursor / Windsurf / Cline / Continue   | ✅ MCP                            | —                                                       |
| ChatGPT Desktop                        | ⚠️ MCP (Developer Mode beta)     | Enable Developer Mode in the app                        |
| claude.ai web                          | ❌                                | Install Claude Desktop (same account, same memory)      |
| chatgpt.com web                        | ❌                                | Install ChatGPT Desktop + Developer Mode                |
| gemini.google.com                      | ❌                                | CLI manual workflow (below)                             |
| DeepSeek web                           | ❌                                | CLI manual workflow (below)                             |

**CLI manual workflow:**
1. `uvx mneva capture --scope myproj "..."` after an interesting decision in chat.
2. `uvx mneva search "topic"` before asking a new AI a follow-up.
3. Copy matching records from terminal output into the new chat as context.

### Alternative installs

- **`pipx install mneva`** — still supported. Existing v0.1.x users running `pipx upgrade mneva` get both `mneva` and `mneva-mcp` console scripts.
- **`uv tool install mneva` + `uv tool upgrade mneva`** — preferred over bare `uvx mneva` when you want a single pinned install that you upgrade explicitly (`uvx` resolves on first run and caches; `uvx mneva@latest` forces a fresh resolve).
- **From source:** `git clone https://github.com/mneva-ai/mneva.git && cd mneva && pip install -e ".[dev]"`.

### Updating mneva

```sh
mneva upgrade
```

`mneva upgrade` detects how mneva was installed (`pipx` / `uv tool` / `uvx` / `pip`) and runs the matching update command, so you don't have to remember which one you used. Pass `--dry-run` to print the command without running it. If you run the MCP server via `uvx --from mneva mneva-mcp`, uvx already fetches the latest published version on each run, so there is nothing to upgrade.

### Advanced — BYOK LLM features

`mneva synthesize`, `mneva digest`, and `mneva distill` use an external LLM provider for summarization and record extraction. They require a key in your environment (Anthropic / OpenAI / Google / OpenRouter — pick one). These are power-user features, not part of the headline MCP path.

- `mneva synthesize --scope X --backend anthropic` — two-stage Stage 1 / Stage 2 brainstorming over a scope.
- `mneva digest --scope X --backend anthropic --write-bootstrap` — distills a scope into a `bootstrap.md` you can paste into a new tool session.
- `mneva distill --source path/to/transcript.md --scope X` — extracts permanent records from a raw conversation transcript. Cost-gated; pass `--yes` to skip the prompt.

See [`docs/providers.md`](./docs/providers.md) for per-provider setup.

### Observability (opt-in)

`mneva diagnose [--share]` prints a sanitized status report (platform, Python version, record counts by lifespan, configured backends, per-MCP-client attribution counts, last activity timestamp). The output goes to stdout only — mneva never sends it anywhere. Run it and paste the result into a bug report when something looks off.

### Testing

Tests use **pytest** with `pytest-asyncio` and `pytest-cov`. From a source checkout with dev extras installed:

```sh
pytest
```

CI runs the full matrix (ubuntu / macos / windows × Python 3.11 / 3.12 / 3.13 / 3.14) on every PR via [`.github/workflows/ci.yml`](./.github/workflows/ci.yml).

---

## Roadmap

mneva is in **alpha**. v0.2 ships the MCP layer plus uvx-first install. Milestones:

- [X] **v0.1.0** — CLI + store + BM25/sqlite-vec index + replay templates + HTTP API + four-provider BYOK
- [X] **v0.1.x** — Gap fixes, Obsidian vault read-write integration, `mneva distill`, CI matrix forward-defense
- [X] **v0.2** — MCP server (`mneva-mcp` console script + 6 FastMCP tools), `uvx`-first install, WAL concurrency for cross-process safety, opt-in `mneva diagnose --share` observability
- [ ] **v0.3** — Browser extension (Chrome / Firefox / Edge, Manifest V3) so chat UIs that cannot spawn MCP subprocesses (chatgpt.com, claude.ai web, gemini.google.com, DeepSeek) still see mneva. Entry condition: ≥10 real users + ≥3 explicit asks via `mneva diagnose --share`.
- [ ] **v1+** — Native GUI installer for non-technical users; optional hosted `mneva.app` SaaS for phone / multi-device sync.

---

## Contributing

- **💬 [Join the Discussions](https://github.com/mneva-ai/mneva/discussions)**: Share your insights, provide feedback, or ask questions.
- **🐛 [Report Issues](https://github.com/mneva-ai/mneva/issues)**: Submit bugs found or log feature requests for the `mneva` project.
- **💡 [Submit Pull Requests](https://github.com/mneva-ai/mneva/blob/main/CONTRIBUTING.md)**: Review open PRs, and submit your own PRs.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your GitHub account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.
   ```sh
   git clone https://github.com/mneva-ai/mneva.git
   ```
3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.
   ```sh
   git checkout -b new-feature-x
   ```
4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **Push to GitHub**: Push the changes to your forked repository.
   ```sh
   git push origin new-feature-x
   ```
7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.
8. **Review**: Once your PR is reviewed and approved, it will be merged into the main branch. Congratulations on your contribution!
</details>

<details closed>
<summary>Contributor Graph</summary>
<br>
<p align="left">
   <a href="https://github.com/mneva-ai/mneva/graphs/contributors">
      <img src="https://contrib.rocks/image?repo=mneva-ai/mneva">
   </a>
</p>
</details>

---

## License

Mneva is licensed under the [Apache License 2.0](./LICENSE).

---

## Links

- Website: https://mneva.org
- Repository: https://github.com/mneva-ai/mneva
- PyPI: https://pypi.org/project/mneva/
- Issues: https://github.com/mneva-ai/mneva/issues
- Changelog: [`CHANGELOG.md`](./CHANGELOG.md)

<div align="right">

[![][back-to-top]](#top)

</div>


[back-to-top]: https://img.shields.io/badge/-BACK_TO_TOP-151515?style=flat-square


---
