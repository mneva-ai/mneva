# mneva

**Your AI memory follows you. Switch tools, and every AI still knows who you are.**

Every new AI chat starts from zero, and each app remembers you only inside itself, so you keep re-explaining who you are, what you're working on and how you like answers. mneva keeps one memory as Markdown files on your own computer and carries it into ChatGPT, Claude, Gemini, Grok and Doubao (in Chrome or Edge), plus Claude Code, Codex and the Claude desktop app. Move between them and your memory comes with you. No account, no mneva cloud, and you can open, edit or delete every line.

**English** | [中文](https://github.com/mneva-ai/mneva/blob/main/README.zh-CN.md)

---

## Contents

- [Install in one line](#install-in-one-line)
- [After installing](#after-installing)
- [What works where](#what-works-where)
- [Why plain Markdown files](#why-plain-markdown-files)
- [For developers](#for-developers)
- [Roadmap](#roadmap)
- [Feedback and contributing](#feedback-and-contributing)
- [License](#license)

---

## Install in one line

You don't need Python beforehand. The script installs [uv](https://docs.astral.sh/uv/), which installs mneva and the Python it runs on, then runs `mneva setup` to connect Claude Code, Codex, the Claude desktop app and your browser. Running it again changes nothing.

**Windows:** open PowerShell and paste

```powershell
irm https://raw.githubusercontent.com/mneva-ai/mneva/main/install/install.ps1 | iex
```

**macOS / Linux:** open a terminal and paste

```bash
curl -LsSf https://raw.githubusercontent.com/mneva-ai/mneva/main/install/install.sh | sh
```

**Mainland China:** use the commands in the [Chinese README](https://github.com/mneva-ai/mneva/blob/main/README.zh-CN.md#一行命令安装). They fetch everything from mirrors inside China, and later upgrades keep using the same mirror.

When it finishes, open a new terminal so the `mneva` command is found.

## After installing

Three steps, each done once.

### 1. Write your profile

Setup saved a template at `~/.mneva/profile-template.md` (on Windows: `C:\Users\<you>\.mneva\profile-template.md`). Open it in any text editor and fill in who you are, what you work on and how you want answers. Then save it into mneva:

- **With Claude Code or Codex:** say *"Read ~/.mneva/profile-template.md and save each section to mneva with capture_memory, scope profile, lifespan permanent."*
- **Without them:** save each section from the terminal:

  ```bash
  mneva capture --scope profile --lifespan permanent "I write in Chinese. Keep answers short and give concrete steps."
  ```

Run `mneva brief` to see the profile your AI tools will get.

### 2. Turn on the browser extension

The extension is not in the Chrome or Edge store yet, so you load it by hand once:

1. Open `chrome://extensions` in Chrome, or `edge://extensions` in Edge.
2. Turn on **Developer mode**.
3. Click **Load unpacked** and pick the folder `~/.mneva/extension` (on Windows: `C:\Users\<you>\.mneva\extension`).

New chats on ChatGPT, Claude, Gemini, Grok and Doubao now start with your profile. On any other site, press Alt+Shift+M to insert it. The extension's popup turns it off per site. It reads the profile from your own computer through the bridge `mneva setup` registered: there is no server to run and no token. The profile text goes only into the chats you start.

### 3. Keep it current

- Edit your profile whenever you like: `mneva capture` adds a record, and the Markdown files under `~/.mneva/store/` can be edited directly.
- If you use Claude Code or Codex, `mneva learn` reads the prompts you typed there and proposes edits to your profile. Nothing changes until you accept with `mneva learn --accept 1,2` (or `all`), or drop them with `mneva learn --discard`. Once you have a profile, this runs by itself about once a day when a Claude Code or Codex session starts, and the next conversation mentions any edits waiting for you. Set `MNEVA_LEARN_AUTO=0` to turn that off.
- `mneva upgrade` updates mneva and refreshes the extension, which reloads itself.

## What works where

| Where you use AI | How it gets your profile |
| --- | --- |
| ChatGPT, Claude, Gemini, Grok, Doubao on the web (Chrome, Edge) | The extension adds it to each new chat |
| Any other website | Alt+Shift+M inserts it |
| Claude Code, Codex | Connected by `mneva setup`; read at the start of each conversation |
| Claude desktop app (Windows, macOS) | Connected by `mneva setup`; fully quit and reopen Claude once |
| Phone apps, and anything else | `mneva brief --copy`, then paste into the app's "about you" setting (for ChatGPT add `--max-chars 1500`). mneva reminds you when the profile changes after a copy |

Learning from your web chats, and filling in the phone apps' settings for you, are planned. See the [Roadmap](#roadmap).

## Why plain Markdown files

Most AI memory tools keep your memory in their own database. mneva keeps it in your files.

- **You can read and fix it.** Each record is a Markdown file with a small YAML header under `~/.mneva/store/`. When an AI gets something wrong about you, open the file and change the line.
- **No account, no mneva cloud.** mneva sends nothing about you to any server of its own, and has no telemetry. Only features you turn on reach an outside service: `mneva learn` hands your prompts to your local Claude Code, and the bring-your-own-key commands call the provider whose key you set.
- **Works with your own tools.** Commit the folder to git, review changes in a pull request, or sync it both ways with an Obsidian vault (`mneva sync-vault`).
- **The search index is disposable.** Delete `~/.mneva/mneva.sqlite` and `mneva reindex` rebuilds it from the Markdown. Nothing is lost.

---

## For developers

### Other MCP clients

`mneva setup` connects Claude Code, Codex and the Claude desktop app by itself. For other clients, paste a block like this into the client's MCP config and restart it. mneva creates `~/.mneva/` on first launch.

**Cursor:** create `~/.cursor/mcp.json` (or `.cursor/mcp.json` in your workspace):

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

**Windsurf:** edit `~/.codeium/windsurf/mcp_config.json` with the same shape (`"MNEVA_MCP_CLIENT": "windsurf"`).

**ChatGPT desktop:** MCP support is behind **Developer Mode (beta)** in the app settings. Turn it on and add the same block (`"MNEVA_MCP_CLIENT": "chatgpt-desktop"`).

**Cline / Continue:** both take the same block, scoped to your VS Code workspace.

> **First launch is slow, then instant.** The first run downloads mneva and its dependencies and caches them. If the client reports the server as slow or failed on the very first try, restart the client once. To warm the cache, run `uvx --from mneva mneva-mcp` once in a terminal and press Ctrl-C after it starts.

After a restart, ask the client *"remember that we decided X"* and mneva saves a record you can search next session.

### Command line

```sh
mneva capture --scope my-project --lifespan permanent \
    "decision: use SQLite over Postgres for v0 because zero-ops"
mneva search "SQLite"
mneva replay --tool=claude-code --scope=my-project
mneva reindex   # rebuild the search index after editing the Markdown by hand
```

### Memories that follow your repo

Capture inside a git repository and the record notes where it came from, in its frontmatter:

```yaml
scope: my-project
lifespan: permanent
repo: github.com/mneva-ai/mneva
branch: main
commit_sha: cd6d7af1c3a2982810799d2f023a028fc361c6dc
```

`mneva search` then scopes to the repo you're standing in:

```sh
mneva search "SQLite"                # this repo (plus memories tied to none)
mneva search "SQLite" --all-repos    # everything
mneva capture --scope p --no-git "…" # don't record provenance at all
```

`repo` comes from the normalized remote URL, so it keeps matching after you clone the project somewhere else. Memories captured outside a repo are never hidden; only memories that belong to a *different* repo are filtered out. No git, no repo or no remote just means no provenance.

### Install by hand

You need **Python 3.11 or newer** and, preferably, [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
uv tool install mneva
mneva setup
```

- **pipx:** `pipx install mneva`, then `mneva setup`.
- **No install:** `uvx mneva setup` and `uvx --from mneva mneva-mcp` resolve the latest release on each run.
- **From source:** `git clone https://github.com/mneva-ai/mneva.git && cd mneva && pip install -e ".[dev]"`.

`mneva setup --dry-run` shows what setup would do without doing it. If the Claude desktop config file can't be parsed, setup leaves it untouched and prints the entry to add by hand.

### Updating

```sh
mneva upgrade
```

It detects how mneva was installed (`pipx`, `uv tool`, `uvx` or `pip`), runs the matching update, then reruns `mneva setup` with the new version. That refreshes the browser extension copy, and the extension reloads itself, including in AI tabs that are already open. `--dry-run` prints the commands without running them.

### Bring-your-own-key features

`mneva synthesize`, `mneva digest` and `mneva distill` call an LLM provider (Anthropic, OpenAI, Google or OpenRouter) with a key from your environment. `mneva learn --backend` does the same instead of using your local Claude Code. See [`docs/providers.md`](https://github.com/mneva-ai/mneva/blob/main/docs/providers.md).

- `mneva synthesize --scope X --backend anthropic`: two-stage brainstorming over a scope.
- `mneva digest --scope X --backend anthropic --write-bootstrap`: condenses a scope into a `bootstrap.md` you can paste into a new session.
- `mneva distill --source path/to/transcript.md --scope X`: extracts permanent records from a conversation transcript. Asks before spending; `--yes` skips the prompt.

### Diagnostics

`mneva diagnose [--share]` prints a sanitized status report (platform, Python version, record counts, configured backends, per-client counts, last activity). It only prints; mneva never sends it anywhere. Paste it into a bug report when something looks off.

### Under the hood

- One CLI (`mneva`) and one MCP server (`mneva-mcp`) built on the official `mcp` SDK, with six tools: `capture_memory`, `search_memory`, `forget_memory`, `list_recent_memories`, `replay_context`, `get_status`.
- Storage: Markdown with YAML frontmatter under `~/.mneva/`, indexed in SQLite (WAL mode, safe for several clients at once).
- Search: `rank-bm25` keyword scoring with optional `sqlite-vec` reranking.
- Browser extension: Manifest V3, talking to mneva through Chrome native messaging. Privacy policy: [`docs/privacy.md`](https://github.com/mneva-ai/mneva/blob/main/docs/privacy.md).
- Optional HTTP API (`mneva serve`, FastAPI).

### Testing

```sh
pip install -e ".[dev]"
pytest
```

CI runs ubuntu, macOS and Windows on Python 3.11 to 3.14 for every pull request ([`ci.yml`](https://github.com/mneva-ai/mneva/blob/main/.github/workflows/ci.yml)), and runs both install scripts on clean machines with and without the mirror mode.

---

## Roadmap

mneva is in **alpha**.

- [X] **v0.1**: CLI, Markdown store, BM25 and sqlite-vec index, replay templates, HTTP API, four BYOK providers, Obsidian vault sync, `mneva distill`
- [X] **v0.2**: MCP server (`mneva-mcp`, six tools), `uvx` install, WAL for several clients at once, opt-in `mneva diagnose`
- [X] **v0.3**: git-aware memories, `mneva brief` for tools without MCP, `mneva setup` for Claude Code and Codex
- [X] **v0.4**: browser extension for Chrome and Edge; new chats on ChatGPT, Claude, Gemini, Grok and Doubao start with your profile; `mneva upgrade`
- [X] **v0.5**: `mneva learn` proposes profile edits from the prompts you typed into Claude Code and Codex; nothing changes until you accept
- [X] **v0.6**: `mneva learn` runs by itself about once a day
- [X] **v0.7**: one-line install with a mirror mode for mainland China; `mneva setup` connects the Claude desktop app
- [ ] **Next**: the extension in the Chrome Web Store and Edge Add-ons, so it installs in one click
- [ ] **Then**: optional recording of your web chats, learning from them with Claude Code, Codex or a DeepSeek key, and reviewing suggested edits inside the extension
- [ ] **After that**: writing your accepted profile into each site's own settings, so the phone apps get it too

---

## Feedback and contributing

- **[Open an issue](https://github.com/mneva-ai/mneva/issues)** for bugs, questions and feature requests.
- **Pull requests** are welcome. Fork the repo, work on a branch, run `pytest`, `ruff check .` and `mypy src`, then open a PR against `main` describing what changed and why.

## License

Apache License 2.0, see [LICENSE](https://github.com/mneva-ai/mneva/blob/main/LICENSE).

**Links:** [PyPI](https://pypi.org/project/mneva/) · [Changelog](https://github.com/mneva-ai/mneva/blob/main/CHANGELOG.md) · [Issues](https://github.com/mneva-ai/mneva/issues)
