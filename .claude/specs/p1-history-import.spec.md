# Spec: learn the profile from local AI history (p1-history-import, phase 1)

Status: approved by the founder 2026-10-18, implementation started.

## Problem

The founder wants every AI tool to know their background, preferences and current work without being told again. Today the profile is six hand-reviewed records (`scope: profile`), written once from 413 Claude Code prompts. It goes stale as soon as the work moves on, and keeping it current is manual.

The founder chose "every AI understands me better" over "find old conversations" (2026-10-18), so the deliverable is a better profile, not a transcript archive or a search index.

## Evidence (measured on the founder's machine 2026-10-18)

| Source | What is there | Usable size |
|---|---|---|
| `~/.claude/history.jsonl` | Every prompt typed into Claude Code, 2026-01-14 to today: `{display, pastedContents, timestamp(ms), project, sessionId}` | 17,087 rows; 3,574 after dropping slash commands, 181k chars, spread across all ten months |
| `~/.claude/projects/**/*.jsonl` | Full session transcripts | Pruned after about 30 days (earliest 2026-09-14). Not used: the prompt log above holds the user's own words for longer |
| `~/.codex/sessions/**/*.jsonl` | Full Codex sessions since 2025-09-26; user turns are `response_item` with `payload.type == "message"`, `role == "user"` | 1,412 user turns, 2.4M chars before filtering (injected instructions, images, pasted plans) |
| `~/.codex/history.jsonl` | Codex prompt log | Stops at 2026-04-21, so not used; the session files cover the same prompts |

Injected text that is not the user speaking, seen 5+ times: Claude Code `<task-notification>`, `<command-name>`, `<local-command-stdout>`, `[Request interrupted`; Codex `# AGENTS.md instructions for`, `<environment_context>`, `<turn_aborted>`, `<goal_context>`, `<subagent_notification>`, `PLEASE IMPLEMENT THIS PLAN`, and image placeholders. Codex's `# Context from my IDE setup:` wraps the real request after `## My request for Codex:`.

`claude -p` works as a zero-key extractor: with `--tools "" --strict-mcp-config --setting-sources "" --no-session-persistence --system-prompt ...` a call carries about 500 tokens of overhead. When `ANTHROPIC_API_KEY` is set, Claude Code bills that key instead of the claude.ai login; with the key removed from the child environment the same call runs on the login.

## Solution

`mneva learn` reads the user's own prompts from local Claude Code and Codex history, extracts durable facts about the user, and proposes edits to the existing profile records. The user reviews each edit; only accepted edits are written.

Pipeline:

1. **Collect** user prompts newer than each source's watermark. Drop injected text (list above), slash commands and messages under 5 characters; keep pasted content out (`pastedContents` is ignored, Codex pastes are capped). Cap each message at 1,500 chars, drop exact repeats, redact obvious secrets (API key and private key patterns) before anything leaves the machine.
2. **Extract**: chunk the prompts oldest first (`distill.chunk_text`), one call per chunk on a cheaper model (Sonnet). Output: dated facts about the user (who they are, preferences, tools, projects and their status, priorities). Instructions exclude secrets, health, finances and third parties' personal details.
3. **Merge**: one call on the stronger model with the current profile records plus all facts in date order. Output: edits to the profile, each `update` (existing id, new body), `add` (new body) or `remove` (existing id), with a one-line reason. Newer facts win; finished work leaves "what I'm doing"; total profile stays under 3,000 chars so the 4,000-char brief never drops a section.
4. **Review**: the edits are saved to `~/.mneva/learn-proposal.json` and shown one by one (old text, new text, reason); the user accepts or skips each. Accepted edits go through the normal write path: `write_record(..., overwrite=True)` keeps the record id (the brief, the vault and the index key on it), plus index update and vault mirror.
5. **Report** the number of prompts read per source and the summed `total_cost_usd` from every call.

### Why not the alternatives

- **Append new records per fact**: the brief has a fixed budget; appended facts would push whole sections out of it and old facts would contradict new ones.
- **Mneva's own API providers by default**: needs an API key, which breaks the zero-config rule. They remain available through `--backend`.
- **Full session transcripts**: mostly tool output and AI text, pruned after 30 days for Claude Code, and not about the user.
- **Write without review**: one wrong fact would be inserted into every AI chat. Review stays until proposals prove reliable in dogfooding.

## User stories

- As a heavy AI user, I want mneva to learn my background and current work from what I already typed into Claude Code and Codex, so I never write a profile by hand.
- As the owner of the profile, I want to see and approve every change before it reaches my AI tools.
- As a user whose work moves on, I want finished projects to leave "what I'm doing" and new ones to enter it.

## Module breakdown

| Module | Responsibility |
|---|---|
| `src/mneva/history.py` (new) | Read and filter user prompts from Claude Code and Codex history. Pure file reading, no network. |
| `src/mneva/learn.py` (new) | Watermarks, extract and merge prompts, proposal file, applying accepted edits, and the `mneva learn` click command. |
| `src/mneva/providers/claude_cli.py` (new) | `Provider` over `claude -p`: login first (API key removed from the child env), the key as fallback when no login works; accumulates `cost_usd`. |
| `src/mneva/cli.py` | Registers the command only, like `upgrade`. |

## Interface design

- `mneva learn [--backend claude-code|anthropic|openai|google|openrouter] [--all]`. `--all` ignores the watermarks (re-learn from the start). If a proposal is pending, `learn` reviews it first instead of making a new one.
- `~/.mneva/learn-state.json`: `{"claude-code": <last ms timestamp>, "codex": "<last ISO timestamp>"}`, written after a proposal is saved, so a rerun with no new prompts makes no calls.
- `~/.mneva/learn-proposal.json`: `{"created": iso, "prompts": {source: n}, "cost_usd": x, "edits": [{"op", "id", "body", "reason"}]}`.
- Bookkeeping only: deleting either file loses no record.

## Acceptance criteria

Code-level (unit and integration tests, fixtures built from the measured shapes):

1. Injected text, slash commands, short messages, repeats and pasted content never reach a prompt; secrets are redacted.
2. A second run with no new prompts makes no model call and writes nothing.
3. Nothing reaches the store until the user accepts an edit; an `update` keeps the record id; a `remove` deletes only that record.
4. The claude CLI is called with tools, MCP servers, settings and session persistence all off. (Persistence must stay off: otherwise each learn run writes a session that the next run reads.)

Release gate (real data, not fixtures): the founder runs `mneva learn` on their own Claude Code and Codex history, reads every proposed edit, and judges whether the result is closer to who they are and what they do now than profile v1. Reported with prompt counts and the real cost.

## Out of scope (phase 1)

- Automatic daily runs and surfacing pending proposals in MCP or the extension (next phase).
- ChatGPT and Claude web exports, Gemini and Doubao.
- Recording web chats through the extension.
- Records outside `scope: profile`.
