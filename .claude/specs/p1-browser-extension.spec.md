# Spec: browser extension (p1-browser-extension)

Status: approved direction 2026-10-16, implementation not started.

## Problem

The founder uses ChatGPT, Claude, Doubao and Gemini in the browser every day. None of them can run a local MCP server, so today the profile reaches them only by `mneva brief --copy` and a manual paste, repeated whenever the profile changes. The founder rejected even a small `--for <tool>` flag as too much work: mneva must run by itself once installed. Goal stated by the founder: the easiest possible path for users.

Evidence that the core mechanism works (checked 2026-10-16 in the founder's logged-in Chrome): `document.execCommand("insertText")` into the composer inserts multi-line Chinese text correctly on chatgpt.com, claude.ai and gemini.google.com; select-all plus delete clears it again. doubao.com redirected to a region-ban page from that network and is unverified.

## Solution

A Manifest V3 extension for Chrome and Edge. When the user opens a new conversation on a supported site and the composer is empty, the extension inserts the current profile brief followed by a blank line, and the cursor ends after it, so the user types the question underneath. On any other site, a keyboard shortcut inserts the brief into the focused text field.

The extension reads the brief through Chrome native messaging. `mneva setup` registers a small native host (`python -m mneva.native_host`) that Chrome starts on demand. The extension therefore never talks to the network, needs no server running, and needs no token.

### Why not the alternatives

- `mneva serve` over localhost HTTP: needs a long-running process and a token in the extension; native messaging needs neither.
- Remote MCP connector: covers only Claude and ChatGPT, needs a tunnel, an always-on machine and auth. Kept for later, for the Claude phone app only.
- Writing into each site's "about you" settings page: settings pages change more often than composers, and a silent write into account settings is harder for the user to see and undo.
- Prepending the profile invisibly at send time: the user cannot see or edit what is sent. Visible insertion keeps the user in control.

## User stories

- As a heavy AI user, I want a new ChatGPT, Claude, Gemini or Doubao chat to start with my current profile, so I never re-explain who I am.
- As a user who just edited my profile in Claude Code, I want the next new chat to carry the new version, with nothing to re-copy.
- As a user who sometimes wants a plain chat, I want to switch the auto-insert off per site.
- As a user of ChatCut, Runway or any other site, I want one shortcut that inserts my profile into the field I am typing in.

## Module breakdown

| Module | Responsibility |
|---|---|
| `src/mneva/native_host.py` | Native messaging host: length-prefixed JSON over stdio; answers `ping` and `get_brief`; nothing else. Also `register(...)`: writes the host manifest and launcher and registers them for Chrome, Edge and Chromium (Windows registry under HKCU; macOS and Linux manifest directories). Idempotent, honours dry-run. |
| `src/mneva/setup.py` (extend) | Thin orchestrator: calls `native_host.register(...)` and prints the extension path for "Load unpacked". |
| `src/mneva/extension/` | The extension, shipped inside the wheel so `mneva setup` can print its path for "Load unpacked". `manifest.json`, `background.js` (service worker, native messaging), `content.js` (site adapters, insertion), `popup.html`/`popup.js` (status, per-site toggles). |

## Interface design

Native host messages (Chrome framing: 4-byte little-endian length, UTF-8 JSON):

```
-> {"type": "ping"}
<- {"ok": true, "version": "0.4.0"}

-> {"type": "get_brief", "max_chars": 4000}
<- {"ok": true, "text": "...", "records": 6}
<- {"ok": false, "error": "no_profile", "message": "Add profile records first: ..."}
```

Unknown types and malformed input return `{"ok": false, "error": "bad_request"}`. `max_chars` is clamped to 1..20000. The host only renders the brief; it writes nothing and runs nothing else.

Host registration name: `org.mneva.brief`. `allowed_origins` is a list built for two IDs: the dev ID pinned by a public `key` in `manifest.json` (private key not committed), and later the Chrome Web Store ID, which differs because the store rejects `key` and assigns its own. Chromium is registered too so Playwright's bundled Chromium can exercise extension to host end to end.

Host rules, each of which is a silent total failure if broken:

1. Binary stdio: read `sys.stdin.buffer`, write `sys.stdout.buffer`, and on Windows `msvcrt.setmode(fd, os.O_BINARY)` on both, or `\n` becomes `\r\n` and corrupts the length prefix.
2. Import only `mneva.brief`, never `mneva.cli` (it reconfigures stdout at import) or `mneva.mcp_server` (it writes to stderr on start).
3. Nothing but frames on stdout; diagnostics go to stderr.
4. The launcher reuses `setup.server_argv()`'s install detection (uvx versus a stable interpreter): a `.bat` with `@echo off` on Windows, a `#!/bin/sh` script with the exec bit elsewhere. The manifest `path` is absolute.
5. Exit cleanly on EOF, which is how Chrome signals disconnect.

Site adapters (selectors verified 2026-10-16 except Doubao):

| Site | New-chat URL | Composer |
|---|---|---|
| chatgpt.com | `/` or `/g/<id>` (not `/c/<id>`) | `form .ProseMirror[contenteditable="true"]` |
| claude.ai | `/new` | `[data-testid="chat-input"]` |
| gemini.google.com | `/app` exactly | `rich-textarea .ql-editor[contenteditable="true"]` |
| www.doubao.com | `/chat/` without an id (unverified) | largest visible `textarea` or `[contenteditable="true"]` (unverified) |

Insert rule: on page load and on each SPA URL change, if the URL is a new chat, the site is enabled, the composer exists (wait up to 10 s) and is empty, insert once for that URL. Never insert into a composer that already has text.

Shortcut: `Alt+Shift+M` inserts into the focused editable element on any site (`activeTab` + `scripting`, no host permission needed).

Storage: `chrome.storage.sync` holds per-site on/off (default on). No profile text is stored by the extension.

## Acceptance criteria

1. `native_host` answers `ping` and `get_brief` with correct framing; malformed frames, unknown types and oversized lengths return `bad_request` without crashing. (pytest, subprocess with real stdin/stdout bytes)
2. `mneva setup` on Windows writes the manifest, a launcher, and `HKCU\Software\Google\Chrome\NativeMessagingHosts\org.mneva.brief` plus the Edge key; a second run changes nothing; `--dry-run` writes nothing. (pytest with `winreg` faked)
3. The manifest's `allowed_origins` contains exactly the extension ID derived from the committed public key. (pytest)
4. On a local fixture page that mimics each adapter's composer (ProseMirror div, Quill div, textarea), loading the content script inserts the brief once, does not insert when the composer has text, and does not insert on a non-new-chat URL. (Playwright, optional dev dependency, skipped when absent)
5. Before packaging, the content script body runs in the three live sites through the browser tool and inserts once on a new chat, not on an existing chat, and survives an SPA navigation to a new chat.
6. Dogfood on the founder's Chrome: one week of new chats on ChatGPT, Claude and Gemini start with the profile; recorded in the re-explain log.

## Known costs

- Until the store listing, installing is manual once: developer mode, then "Load unpacked" at the path `mneva setup` prints. This is the one place the zero-config rule is not yet met.
- The inserted block is long (about 1,800 characters for the founder's profile) and visible in every new chat. Per-site toggles exist; a shorter composer budget is a one-line change if the dogfood week shows it is too much.

## Out of scope

Chrome Web Store listing (after the dogfood week), Firefox and Safari, phone apps, syncing site settings pages, capturing memories from web chats, the remote connector.
