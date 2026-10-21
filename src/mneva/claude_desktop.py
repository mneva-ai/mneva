"""claude_desktop.py — register mneva's MCP server with the Claude desktop app.

Claude desktop has no `mcp add` command, so unlike Claude Code and Codex it
is registered by editing its config file. The edit is a merge: other servers
and settings are kept, an existing `mneva` entry is left alone, and a file
that does not parse is never rewritten (the user may be mid-edit, and
overwriting would lose their other servers).

The Microsoft Store build of Claude may read a virtualized copy of this file.
On the founder's Store install `%APPDATA%\\Claude` resolves to the package's
own folder, so the plain path works there; if a build ignores it, the
fallback is a `.mcpb` bundle (see .claude/specs/p1-web-users.spec.md).
"""
from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CONFIG_NAME = "claude_desktop_config.json"
SERVER_NAME = "mneva"
CLIENT_ID = "claude-desktop"
_LABEL = "Claude desktop"


def config_dir(
    platform: str = sys.platform,
    env: Mapping[str, str] = os.environ,
    home: Path | None = None,
) -> Path | None:
    """Where Claude desktop keeps its config, or None where it does not exist."""
    home = home if home is not None else Path.home()
    if platform == "win32":
        appdata = env.get("APPDATA")
        return Path(appdata) / "Claude" if appdata else None
    if platform == "darwin":
        return home / "Library" / "Application Support" / "Claude"
    return None


def entry(server: list[str]) -> dict[str, Any]:
    return {
        "command": server[0],
        "args": server[1:],
        "env": {"MNEVA_MCP_CLIENT": CLIENT_ID},
    }


def _manual_hint(path: Path, server: list[str]) -> str:
    snippet = json.dumps({SERVER_NAME: entry(server)}, indent=2)
    return f"add this under \"mcpServers\" in {path} yourself:\n{snippet}"


def register(server: list[str], *, dry_run: bool, folder: Path | None) -> tuple[bool, str]:
    """Add mneva to the config in ``folder`` (from `config_dir`).

    Returns (ok, line for the user).
    """
    if folder is None:
        return True, f"{_LABEL}: not available on this system, skipped"
    if not folder.is_dir():
        # The folder appears once Claude desktop has run; creating it for a
        # user who does not have the app would only leave clutter behind.
        return True, f"{_LABEL}: not found, skipped"
    path = folder / CONFIG_NAME
    config: Any = {}
    if path.exists():
        try:
            # utf-8-sig: Notepad and PowerShell 5 save JSON with a BOM.
            config = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            return False, f"{_LABEL}: could not read {path} ({e}); left it unchanged, " + (
                _manual_hint(path, server)
            )
    servers = config.get("mcpServers", {}) if isinstance(config, dict) else None
    if not isinstance(servers, dict):
        return False, f"{_LABEL}: {path} has an unexpected layout; left it unchanged, " + (
            _manual_hint(path, server)
        )
    if SERVER_NAME in servers:
        return True, f"{_LABEL}: already registered, left unchanged"
    if dry_run:
        return True, f"{_LABEL}: would add mneva to {path}"
    config["mcpServers"] = {**servers, SERVER_NAME: entry(server)}
    # Write a sibling file and swap it in, so a crash mid-write cannot leave
    # Claude with a truncated config.
    tmp = path.with_name(path.name + ".mneva-tmp")
    try:
        tmp.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        return False, f"{_LABEL}: failed to write {path} ({e})"
    return True, (
        f"{_LABEL}: added to {path}. Quit Claude fully (also from the tray icon) "
        "and reopen it to load mneva."
    )
