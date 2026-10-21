# Spec: a profile that keeps itself current for web and phone users (p1-web-users)

Status: direction approved by the founder 2026-10-20 after three grilling rounds (Q1 to Q22). Engineering review done the same day; all ten findings accepted and folded in below (report at the end). Release 1 next.

## Problem

People besides the founder will install mneva. They are ordinary workers: some use a terminal, most use AI through web pages, desktop apps and phone apps (ChatGPT, Claude, Doubao, Gemini, Grok). Some are in mainland China. The founder wants their profile to need no upkeep: it keeps itself current, and only asks for an occasional "accept" click.

Today that does not work for them, for four separate reasons:

1. **Install.** It needs Python, `pip install mneva`, `mneva setup`, then Developer mode and "Load unpacked" in Chrome. Mainland users also hit slow or blocked GitHub and PyPI downloads, and cannot reach the Chrome Web Store.
2. **Learning material.** `mneva learn` reads Claude Code and Codex history. A web-only user has none.
3. **Learning engine.** `learn_auto` needs a `claude` login. Free Gemini CLI (ended 2026-06-18) and free Qwen OAuth (ended 2026-04-15) are gone, so there is no free CLI engine left.
4. **Phone.** The extension only fills new chats in the desktop browser. A chat started in a phone app sees nothing. Account-level settings (ChatGPT custom instructions, Claude personal preferences, Doubao, Gemini and Grok equivalents) do sync to the phone, per the founder's own check, but today the user must paste into them by hand and re-paste whenever the profile changes.

## Strategy change (recorded in CLAUDE.md, 2026-10-20)

The target widens from people who work through CLI agents to ordinary workers who mainly use web and phone AI apps, including mainland China. Desktop app, landing page and Reddit outreach stay out: the install entry point is the README. Validation adds one real ordinary user per release, installing alone from the README, on top of the founder's dogfooding.

## Solution: three releases, each usable on its own

### Release 1: it installs

- **One-line install.** `install.ps1` (Windows) and `install.sh` (macOS, Linux) in the repo. Each installs uv with the official installer, runs `uv tool install mneva` (uv fetches its own Python, so none is needed beforehand), then `mneva setup`. The English README gives the default command. The Chinese README gives a mainland command that fetches the script through jsDelivr and sets `UV_DEFAULT_INDEX` to the Tsinghua PyPI mirror and `UV_PYTHON_INSTALL_MIRROR` to the npmmirror python-build-standalone mirror. No automatic location detection: a network probe misjudges and is hard to debug.
- **PATH inside the install run.** Right after install, the directories holding `uv` and `mneva` are not yet on the current shell's PATH, so a plain `mneva setup` would fail with "command not found". The scripts call both by full path (the uv install directory, then `uv tool dir --bin`), and finish with `uv tool update-shell` so terminals opened later find `mneva` too.
- **Mainland download chain.** Every download in the chain needs a reachable source: the install script itself, the uv installer and uv binary (GitHub and astral.sh by default; `UV_INSTALLER_GITHUB_BASE_URL` or a mirrored binary), Python builds, and PyPI. Before writing the scripts, each link's mainland source is looked up and recorded in this spec. jsDelivr is intermittent in mainland China, so the Chinese README carries a Gitee mirror of the script as a second command. Verification blocks github.com, astral.sh and pypi.org in the hosts file; that only simulates mainland conditions, and the real check is the release's real user (criterion 6).

  Chain as looked up on 2026-10-20 (files exist and download from a US address; speed inside mainland China unverified). The mainland command sets `MNEVA_MIRROR=cn`, and the script fills in the rest, so the mirror list lives in one place:

  | Link | Default | Mainland |
  |---|---|---|
  | Install script | raw.githubusercontent.com | jsDelivr; second source on Gitee or CNB (cnb.cool raw answered anonymously; Gitee raw redirects to a signed URL that could not be tested from abroad). Either needs a founder account. |
  | uv, all systems | astral.sh installer | the uv wheel from the Tsinghua PyPI mirror, newest by version number (the index is not in version order), checked against the index's sha256, `uv` and `uvx` unpacked into `~/.local/bin`. USTC's uv mirror was tried and dropped: it refuses PowerShell's default requests and returned 403 to a GitHub Linux runner. |
  | Python builds | GitHub | `UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone` |
  | Packages | pypi.org | `UV_DEFAULT_INDEX`: the first of Tsinghua (`https://pypi.tuna.tsinghua.edu.cn/simple`) and Tencent (`https://mirrors.cloud.tencent.com/pypi/simple`) that answers, used for the uv wheel as well. Added after a CI run could not connect to Tsinghua at all. |
- **Claude desktop app.** `mneva setup` adds mneva to `claude_desktop_config.json` (merge, never overwrite other servers). This is new code with its own cases: Claude's folder does not exist, or the system is Linux (Claude desktop is not installed: skip, as setup already does for a missing Claude Code); the folder exists but the file does not (create it); the file is not valid JSON (leave it untouched, tell the user, and print the entry to add by hand); the entry already exists (no change). After a change, setup tells the user to fully quit and reopen Claude. The Microsoft Store build may read a virtualized copy and ignore that file; this is tested on the founder's machine (a Store install) first. If the app does not show mneva, switch to a `.mcpb` bundle (`server.type: "uv"`) that setup opens, and the user clicks Install in Claude.
- **Store listings.** Chrome Web Store and Microsoft Edge Add-ons (reachable from mainland China). The founder registers both developer accounts and pays the Chrome fee. Claude prepares listing text (English and Chinese), screenshots, privacy policy (a file in this repo, linked from the listing), permission justifications and the Limited Use statement. The listing states one purpose: keep your AI profile in sync across AI chat sites. Release 2's recording changes what the extension reads, so it goes back through review with updated disclosures. Each store assigns its own extension ID; both go into `native_host.STORE_EXTENSION_IDS`, and the dev ID stays allowed.
- **Store package.** The stores reject the `key` field that `manifest.json` carries for the stable dev ID. A build script (`store/build.py`) copies the extension, drops `key`, and writes the upload zip; a test checks the zip has no `key` and the same files as the source. Once the store pages exist, setup stops teaching Developer mode and "Load unpacked" and instead says: if you loaded the developer copy, remove it (two copies would insert the profile twice).
- **Host and extension versions (fixed in release 1, used from release 2 on).** A store install updates from the store; the mneva on the user's machine does not follow. `ping` returns the host version and the list of message types it supports. Before sending any message the host may not know, the extension checks that list; when the type is missing, it tells the user to run `mneva upgrade` instead of showing a generic `bad_request`. A `ping` reply without `supports` comes from a host older than release 1 (0.6.x and before) and is treated as supporting only `ping` and `get_brief`. One-line installs are `uv tool` installs, which `upgrade.detect_install_method` already reports as `UV_TOOL` (upgrade runs `uv tool upgrade mneva`, the host launches through the tool's own interpreter by full path).
- **Fix:** setup's closing text names only Chrome and leaves out Grok. Name Chrome and Edge, list all five sites, and point at the store pages once they exist.

### Release 2: it keeps itself current

- **Recording (opt-in).** On the five sites the extension records the user's prompts, the AI's replies, and the name and type of each uploaded file. It does not capture file contents: the AI's reply about a file serves as its summary. Nothing is recorded until the user clicks "Agree" on a consent page shown the first time the extension opens. The popup pauses recording per site and clears all recordings. Recordings stay on this machine under `~/.mneva/web-history/` and are kept until the user clears them. The block mneva itself inserted into a chat is never recorded.
- **Recording in batches.** Each native message starts a new Python process (about 0.2 s measured). The extension does not send one message per chat turn: it keeps recordings in `chrome.storage.local` and hands them to the host in one `record_batch` every few minutes or once a batch fills, and again when the browser goes idle. A batch the host did not confirm stays queued and is resent.
- **What learning may believe.** Facts in the profile must come from the user's own words. AI replies are context for reading those words, never a source of facts by themselves (an earlier test proposal claimed the user could "remember all history", which came from AI phrasing). A prompt rule alone cannot enforce this: an AI reply can be phrased as "you said earlier you want answers in French". So every proposed fact carries a short verbatim quote from the user, and code checks that the quote appears in a `role: "user"` turn of the material; a fact whose quote is missing or found only in assistant text is dropped before the proposal is saved. Each run still takes the newest 120k characters, user prompts first.
- **Engines.** In order: Claude Code login (`claude -p`), Codex login with ChatGPT Plus or higher (`codex exec --ephemeral --ignore-user-config --skip-git-repo-check --json -`, read-only sandbox), or a DeepSeek API key the user pastes once into the extension settings. With none, the extension says plainly that the profile will not update by itself. If the user has a subscription but not the CLI, the settings page shows that vendor's official install command and login hint; the install script installs neither, because login has to happen in the user's browser anyway.
- **Trigger.** The native host calls `learn_auto.maybe_start()` when the extension connects, with the same gates as today (20 h since the last finished run, enough new material, no pending proposal, no fresh lock). The engine gate changes: today `should_start` requires `claude` on PATH, so a Codex-only or DeepSeek-only user would never learn; it now passes when any of the three engines is usable. Importing `learn_auto` costs about 0.5 s, so the host writes its reply first and only then imports it and checks the gates.
- **Review in the extension.** A badge shows the number of pending edits. The popup lists each edit with its reason; accept all, accept some, or discard. Nothing changes until accepted. `mneva learn --accept` keeps working in the terminal.
- The DeepSeek key is the one exception to the zero-config rule, accepted because no free engine exists.

### Release 3: the phone has it too

- After the user accepts edits, the extension writes the profile into each site's account settings field, replacing only the part between mneva's own markers and leaving the user's other text untouched.
- When a field is too small (free ChatGPT custom instructions are about 1,500 characters), the engine writes a short version (who I am, preferences, current priorities) that is shown on the accept page and written only after acceptance.
- When a write fails (site changed, not logged in), the extension copies the text, opens that site's settings page and asks the user to paste. It never blocks.
- All five sites. The remote connector stays later, for the Claude phone app only.

### Why not the alternatives

- **Double-click installer (.exe, .pkg):** unsigned ones trigger SmartScreen and Gatekeeper warnings that scare ordinary users more than a pasted command; signing costs a yearly fee; and it edges toward the excluded desktop app. Revisit only if real users stall at the terminal step.
- **Capturing file contents at upload:** intercepting uploads breaks on every site change, needs a vision model for images, costs an engine call per file, and makes store review harder.
- **Applying learned edits automatically:** a false edit would land in every AI tool's settings at once.
- **Writing settings without an accept click:** the 2026-10-16 spec rejected silent writes to account settings. The accept click is what makes release 3 acceptable.

## User stories

- As an ordinary Windows user, I paste one line into a terminal, press Enter, click "Add" in the extension store, and my AI tools start using my profile.
- As a mainland China user, I use the Chinese README's command and the Edge store, and every download comes from a reachable mirror.
- As a web-only user, I agree once to recording, and a week later mneva proposes profile changes from my own chats.
- As a user without Claude or ChatGPT Plus, I paste a DeepSeek key once, or I am told clearly that my profile will not update by itself.
- As a phone user, after I accept changes on my computer, a new chat on my phone already reflects them.
- As a privacy-minded user, I pause recording on one site, or clear all recordings, from the popup.

## Module breakdown

| Module | Release | Responsibility |
|---|---|---|
| `install/install.ps1`, `install/install.sh` | 1 | Install uv, `uv tool install mneva`, `mneva setup`, calling each by full path; `uv tool update-shell`. Mirror variables honoured when set. Idempotent. |
| `.github/workflows/install-verify.yml` | 1 | New job on every PR: run both scripts on clean Windows, macOS and Linux runners against the wheel built from the PR. |
| `src/mneva/setup.py` | 1 | Claude desktop registration with its edge cases; closing text fix; store wording. |
| `src/mneva/native_host.py` | 1, 2 | Store IDs; `ping` lists supported types; new messages below; starts `learn_auto` after replying. Still imports neither `mneva.cli` nor `mneva.mcp_server`. |
| `docs/privacy.md`, `store/` | 1 | Privacy policy; listing text and screenshots; `store/build.py` builds the upload zip without `key`. |
| `src/mneva/web_history.py` | 2 | Append and read recordings; clear; per-site counts. Feeds `history.py` as one more source. |
| `src/mneva/providers/codex_cli.py`, `providers/deepseek.py` | 2 | Engines behind `providers/base.py`. Codex login only, never a key. DeepSeek reads a key stored in `~/.mneva`, never in extension storage. |
| `src/mneva/learn.py` | 2 | Prompt rule: user words are the only source of facts; each fact carries a user quote; code drops facts whose quote is not in a user turn. Engine choice order. |
| `src/mneva/learn_auto.py` | 2 | Engine gate accepts any of the three engines. |
| `src/mneva/extension/` | 1, 2, 3 | Version check against `ping`; consent page; recording in `content.js` with a local queue; review UI in the popup; settings writers per site; English and Chinese strings by browser language. |

## Interface design

`ping` (release 1) gains the list of supported message types:

```
-> {"type": "ping"}
<- {"ok": true, "version": "0.7.0", "supports": ["ping", "get_brief", ...]}
```

New native host messages from release 2, same framing and `bad_request` rules as today. `record_batch` is refused unless the consent flag in `~/.mneva/web-consent.json` is set.

```
-> {"type": "consent", "agree": true}
-> {"type": "record_batch", "items": [{"id": "<uuid>", "site": "chatgpt.com", "chat": "<url>",
    "role": "user"|"assistant", "text": "...", "files": [{"name": "a.pdf", "type": "application/pdf"}],
    "at": "<iso>"}, ...]}
                                         <- ids written; the extension drops only confirmed items,
                                            and the host skips ids it already holds, so a resend
                                            never duplicates
-> {"type": "history_status"}            <- per-site counts, paused sites
-> {"type": "history_clear"}
-> {"type": "get_proposal"}              <- edits with reasons, or none
-> {"type": "accept", "items": "all" | [1, 3]}
-> {"type": "discard"}
-> {"type": "engine_status"}             <- which engine is usable, or why none
-> {"type": "set_deepseek_key", "key": "..."}
-> {"type": "get_settings_text", "site": "chatgpt.com", "max_chars": 1500}
```

Limits: `text` up to 100,000 characters per item (larger replies are truncated with a marker). The host caps each request at `native_host._MAX_REQUEST_BYTES`, 64 KiB today, which one long item already exceeds; release 2 raises it to 4 MiB, and the extension closes a batch before it reaches that size. The host rejects items for sites outside the five.

Recording format: JSON Lines, one file per site per month, `~/.mneva/web-history/<site>/<YYYY-MM>.jsonl`. These are raw material, not memory records, so they are not Markdown and not indexed.

Settings markers: `[mneva profile start]` and `[mneva profile end]`, plain text so every site's field keeps them.

## Acceptance criteria

Release 1:
1. On a clean Windows user account, the one-line command installs uv, mneva and the native host with no Python installed beforehand, in one run of the same terminal; a second run changes nothing; a newly opened terminal finds `mneva`. (manual, recorded in the progress log)
2. The mainland command works with github.com, astral.sh and pypi.org blocked in the hosts file, using only the recorded mirrors; the Gitee command works with jsDelivr blocked too. (manual)
3. On every PR, CI runs both install scripts on clean Windows, macOS and Linux runners against the PR's wheel, then checks `mneva --version` and that the native host manifest is registered. (CI)
4. `mneva setup` adds mneva to the Claude desktop config without touching other servers; a missing Claude folder is skipped and a missing file in an existing folder is created; an invalid JSON file is left byte for byte and the user is told what to add; a second run changes nothing; `--dry-run` writes nothing; after a change the output says to restart Claude. (pytest)
5. After setup on the founder's machine, the Claude desktop app lists mneva's tools; if not, the `.mcpb` path is built and passes the same check.
6. One real ordinary user installs from the README alone on their own machine, without help. (manual, recorded)
7. `store/build.py` produces a zip whose manifest has no `key` and whose files match the extension folder. (pytest)
8. `ping` returns `supports`. (pytest) The extension side, telling the user to run `mneva upgrade` when a type it needs is missing, is built and checked in release 2 against a faked old host, because release 1's extension sends no new type yet.
9. The extension is published on both stores, a store install reads the brief through the native host, and setup's text points to the store pages and says to remove a developer copy. (manual, plus pytest for the text)

Release 2:
10. Nothing is recorded before consent; after consent, a prompt and a reply on each of the five sites land in `web-history` through `record_batch`; an unconfirmed batch is resent and not duplicated; pause and clear work. (pytest for the host, browser tool check per site)
11. A learn run whose only material is web history proposes edits; a fake provider reply with a fact quoted only from an assistant turn, and one with no quote, both lose that fact before the proposal is saved. (pytest; plus one real run)
12. Each engine runs isolated and login-only where applicable; with no engine, `engine_status` says why; `learn_auto` starts for a user who has only Codex or only a DeepSeek key. (pytest with subprocess faked)
13. The host's reply to the extension does not wait for `learn_auto` to import or decide. (pytest: reply written before the learn check runs)
14. The popup shows pending edits; accepting some applies exactly those. (pytest for the host, manual for the UI)
15. One real user, after a week, has a proposal they accepted. (manual)

Release 3:
16. On each of the five sites, accepting edits rewrites only the marked part of the settings field and keeps the user's other text. (browser tool check per site)
17. A field too small for the profile gets the short version, shown before acceptance. (pytest)
18. A failed write falls back to copy and open. (manual, by breaking a selector)
19. A new chat on a phone app shows a change accepted on the computer. (manual, real user)

## Risks

- Store review for an extension that reads page content and talks to a native program may take up to about 3 weeks and ask for changes.
- Five sites' chat pages and settings pages change without notice. Recording and settings writes are per-site adapters with a fallback, and each release re-checks them in the browser.
- Engine runs use the user's subscription quota or DeepSeek balance.
- The Claude desktop Store build may ignore the config file (see release 1).
- The mainland download chain is only simulated in testing. A link that works from abroad with hosts blocking can still fail inside mainland China; the release's real user is the first real test.
- Release 2 sends the recording consent and new disclosures through store review again, which can delay that release.

## Out of scope

Desktop app, landing page, outreach; double-click installers; file content capture; Firefox and Safari; automatic location detection; the remote connector (later); Doubao and Gemini phone apps beyond what their account settings provide.

## GSTACK REVIEW REPORT

Engineering review (plan-eng-review), 2026-10-20. Own pass over architecture, code quality, tests and performance, plus an independent outside voice (verdict REVISE). All ten findings accepted by the founder ("按建议写进 spec") and folded into the sections above.

| # | Severity | Finding | Resolution | Release |
|---|---|---|---|---|
| 1 | High | Freshly installed `uv` and `mneva` are not on the running shell's PATH, so `mneva setup` fails | Call both by full path; `uv tool update-shell` | 1 |
| 2 | High | Store auto-updates the extension but not the local host; new messages would hit an old host with a bare `bad_request` | `ping` returns `supports`; extension asks for `mneva upgrade` | 1 |
| 3 | High | Dev copy plus store copy inserts the profile twice; stores reject `key` | `store/build.py` strips `key`, tested; setup says to remove the dev copy | 1 |
| 4 | High | Mainland chain unverified for the uv installer and binary; jsDelivr intermittent | Look up and record every link before coding; Gitee second command; hosts-file simulation; real user | 1 |
| 5 | Medium | Install scripts have no CI | PR job on clean Windows, macOS, Linux runners against the PR wheel | 1 |
| 6 | Medium | Claude desktop registration is new code with unhandled cases | Missing file, invalid JSON (untouched), existing entry, restart notice; each tested | 1 |
| 7 | Medium | One Python process (about 0.2 s) per recorded message | Queue in the extension; `record_batch` with resend | 2 |
| 8 | Medium | `learn_auto` only starts when `claude` is on PATH | Gate passes on any of the three engines | 2 |
| 9 | Medium | A prompt rule cannot stop an AI reply posing as the user's words | Each fact carries a user quote; code drops facts whose quote is not in a user turn | 2 |
| 10 | Low | Importing `learn_auto` (about 0.5 s) delays the host reply | Reply first, then import and check | 2 |

Considered and not adopted: a persistent `connectNative` port for recording (batching in the extension removes the cost with less lifecycle code); a shared subprocess helper for `claude_cli` and `codex_cli` (wait for the second real use before abstracting).

VERDICT: CLEARED with changes applied. Release 1 may start.

NO UNRESOLVED DECISIONS
