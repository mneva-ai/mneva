<div id="top">

<!-- HEADER STYLE: MODERN -->
<div align="left" style="position: relative; width: 100%; height: 100%; ">

# MNEVA

<em>Persistent agent context substrate. Local-first markdown store that every AI tool can query.</em>

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

---

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Features](#features)
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

mneva is a local-first persistent context substrate for AI-assisted development. It captures, indexes, and replays your project's insights, decisions, and history across sessions, ensuring your AI tools never start from a blank slate.

**Why mneva?**

This project eliminates session amnesia for AI agents and developers by providing a durable, searchable memory layer that runs entirely on your machine. The core features include:

- **🏠 Local-First Context Store:** All data persists in `~/.mneva` as structured markdown. Your team's knowledge stays private, offline, and under your control.
- **🔍 Hybrid Semantic Search:** Instantly surface relevant context using BM25 keyword matching combined with optional `sqlite-vec` vector reranking, filtered by scope and lifespan.
- **🧩 Multi-Provider AI Engine:** Seamlessly swap between Anthropic, OpenAI, Google, or OpenRouter for synthesis and brainstorming, avoiding vendor lock-in.
- **🔄 Context Replay for AI Tools:** Generate structured prompt blocks that inject captured context directly into your AI coding sessions, cutting out repetitive explanations.
- **🖥️ Dual CLI & API Interface:** Manage your memory interactively via `mneva capture/search/replay` commands, or integrate it into automated pipelines using the built-in FastAPI server.

---

## Features

|      | Component       | Details                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| :--- | :-------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ⚙️  | **Architecture**  | <ul><li>**FastAPI** web service with **Uvicorn** ASGI server</li><li>Async/await design for non‑blocking I/O</li><li>RAG‑like pipeline: **BM25** keyword ranking + **sqlite‑vec** vector similarity</li><li>CLI interface via **Click** (inferred from dependency)</li><li>Modular router structure for separate AI provider endpoints</li></ul>                                                                                                                       |
| 🔩 | **Code Quality**  | <ul><li>Static type checking with **mypy** (config in <code>mypy.ini</code>)</li><li>Linting + formatting with **ruff**</li><li>Code coverage enforced via **pytest‑cov**</li><li>CI workflow (<code>ci.yml</code>) runs lint, type‑check, and tests</li><li>Packaging verified via <code>install-verify.yml</code></li></ul>                                                                                                                                       |
| 📄 | **Documentation** | <ul><li>Apache 2.0 **License** (see <code>LICENSE</code>)</li><li>User docs in <code>docs/</code>: <code>alpha-onboarding.md</code>, <code>providers.md</code></li><li>Inline docstrings on all public CLI commands and API endpoints</li></ul>                                                                                                                                                                                                                  |
| 🔌 | **Integrations**  | <ul><li>**OpenAI** (GPT models)</li><li>**Anthropic** (Claude models)</li><li>**Google Generative AI** (Gemini)</li><li>**rank‑bm25** for keyword retrieval</li><li>**sqlite‑vec** for vector storage & similarity search</li><li>**python‑frontmatter** (YAML/JSON metadata parsing)</li></ul>                                                                                                                                                                       |
| 🧩 | **Modularity**    | <ul><li>Separate provider modules per AI service</li><li>Configuration split across <code>pyproject.toml</code>, <code>mypy.ini</code>, <code>pytest.ini</code>, and CI YAML files</li><li>Clear dev‑vs‑prod dependency groups (testing, linting, packaging)</li><li>Router‑based FastAPI app structure (common pattern)</li></ul>                                                                                                                                    |
| 🧪 | **Testing**       | <ul><li>**pytest** as test runner with **pytest‑asyncio** for async tests</li><li>**pytest‑cov** for coverage measurement</li><li>CI pipeline (<code>ci.yml</code>) executes tests on each push</li><li>Installation verification workflow ensures package builds correctly</li></ul>                                                                                                                                                                                  |
| ⚡️  | **Performance**   | <ul><li>Async request handling via **Uvicorn** and **FastAPI**</li><li>**sqlite‑vec** provides fast approximate nearest neighbor search</li><li>**rank‑bm25** delivers efficient keyword scoring</li><li>No explicit benchmark data; performance limited by single‑node SQLite</li></ul>                                                                                                                                                                               |
| 🛡️ | **Security**      | <ul><li>API keys for AI providers expected via environment variables (standard practice)</li><li>No injection/flaw detection tools visible (e.g., Bandit)</li><li>**httpx** uses HTTPS for outbound calls</li><li>Secrets handling not explicitly enforced in CI</li></ul>                                                                                                                                                                                             |
| 📦 | **Dependencies**  | <ul><li><b>Runtime:</b> <code>fastapi</code>, <code>uvicorn</code>, <code>click</code>, <code>httpx</code>, <code>openai</code>, <code>anthropic</code>, <code>google‑generativeai</code>, <code>rank‑bm25</code>, <code>sqlite‑vec</code>, <code>python‑frontmatter</code></li><li><b>Dev:</b> <code>pytest</code>, <code>pytest‑asyncio</code>, <code>pytest‑cov</code>, <code>ruff</code>, <code>mypy</code>, <code>twine</code>, <code>build</code></li></ul> |

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
									<td style='padding: 8px;'>- Configures the Google Generative AI provider as part of the provider abstraction layer, defaulting to the gemini-2.0-pro model with 1M-token context window<br>- It retrieves the API key from environment variables and exposes a completion interface for generating text responses, seamlessly integrating into the mneva ecosystem for multi-provider support.</td>
								</tr>
								<tr style='border-bottom: 1px solid #eee;'>
									<td style='padding: 8px;'><b><a href='https://github.com/mneva-ai/mneva/blob/main/src\mneva/providers/openai.py'>openai.py</a></b></td>
									<td style='padding: 8px;'>- Provides integration with OpenAIs GPT-5 model as the default provider for completions<br>- Handles API key authentication from environment variables and offers a simple interface to generate text responses<br>- This enables the mneva system to leverage OpenAIs large language models for various tasks.</td>
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
- **pipx** (`pip install --user pipx && python -m pipx ensurepath`, then reopen your terminal)

### Installation

Install the latest release from PyPI:

```sh
pipx install mneva
mneva --version
```

Alternative without `pipx`: `pip install --user mneva`. This installs into your user site-packages and may conflict with pinned dependencies of other tools, so `pipx` is preferred.

To install from source (development):

```sh
git clone https://github.com/mneva-ai/mneva.git
cd mneva
pip install -e ".[dev]"
```

### Usage

Initialize the store, capture a record, and replay it into your AI tool:

```sh
mneva init
mneva capture --scope my-project --lifespan permanent \
    "decision: use SQLite over Postgres for v0 because zero-ops"
mneva search "SQLite"
mneva replay --tool=claude-code --scope=my-project
```

The full walkthrough is in [`docs/alpha-onboarding.md`](./docs/alpha-onboarding.md). Per-tool wiring (Claude Code → `CLAUDE.md`, Cursor → `.cursor/rules/mneva.mdc`, Codex → `AGENTS.md`) is covered there as well.

### Testing

Tests use **pytest** with `pytest-asyncio` and `pytest-cov`. From a source checkout with dev extras installed:

```sh
pytest
```

CI runs the full matrix (ubuntu / macos / windows × Python 3.11 / 3.12) on every PR via [`.github/workflows/ci.yml`](./.github/workflows/ci.yml).

---

## Roadmap

Mneva is in **alpha (v0.1.0)**. The CLI, store, indexer, replay templates, and HTTP API are all working. The next milestones, drawn from the known limitations in [`CHANGELOG.md`](./CHANGELOG.md):

- [X] **v0.1.0** — CLI + store + BM25/sqlite-vec index + replay templates + HTTP API + four-provider BYOK
- [ ] **v0.1.x** — Stability fixes, docs polish, expanded CI matrix (Python 3.14)
- [ ] **v1** — MCP server endpoint, auto-distillation of long scopes
- [ ] **v2** — Opt-in cloud sync (single-user → small-team)

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
