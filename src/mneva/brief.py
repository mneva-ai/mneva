"""brief.py — a paste-ready summary of the personal profile, for AI tools that
cannot reach mneva over MCP (Doubao, Gemini, ChatCut, a video tool's prompt box).

A profile is ordinary records with scope `profile` and lifespan `permanent`, so
it goes through the same Markdown store, vault sync and reindex as everything
else. Unlike replay, the brief ignores `repo`: who you are does not depend on
which repository you happen to be standing in.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import click

from mneva.paths import ensure_home, mneva_home
from mneva.store import iter_records

PROFILE_SCOPE = "profile"

# No vendor limit is assumed: most tools on the target list do not publish
# one. 4000 characters keeps a paste readable. Known limit worth passing
# explicitly: ChatGPT's custom-instructions box takes 1500.
DEFAULT_MAX_CHARS = 4000

HEADER = "About me (from my mneva profile). Use this background when relevant; no need to repeat it back."
_SEPARATOR = "\n\n"
_CLIPBOARD_TIMEOUT_SECONDS = 10

# What each `brief --copy` last put on the clipboard, one entry per scope and
# budget, so no tool name is needed. Bookkeeping, not memory: deleting it
# only loses the reminders, never a record.
COPIES_FILE = "brief-copies.json"


@dataclass(frozen=True)
class BriefResult:
    text: str
    included: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


class ClipboardError(RuntimeError):
    pass


def render_brief(
    *, max_chars: int, scope: str = PROFILE_SCOPE, home: Path | None = None
) -> BriefResult:
    """Pack whole permanent records of *scope* into at most *max_chars*.

    A record that does not fit is skipped, never cut mid-sentence: a truncated
    preference can say the opposite of the full one. Later, smaller records
    may still fit.
    """
    resolved_home = home if home is not None else ensure_home()
    records = [
        r
        for r in iter_records(home=resolved_home)
        if r.scope == scope and r.lifespan == "permanent"
    ]
    if not records:
        return BriefResult(text="")

    parts = [HEADER]
    used = len(HEADER)
    included: list[str] = []
    skipped: list[str] = []
    for r in records:
        body = r.body.strip()
        cost = len(_SEPARATOR) + len(body)
        if used + cost > max_chars:
            skipped.append(r.id)
            continue
        parts.append(body)
        used += cost
        included.append(r.id)

    text = _SEPARATOR.join(parts) if included else ""
    return BriefResult(text=text, included=included, skipped=skipped)


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_copies(home: Path) -> dict[str, dict[str, object]]:
    try:
        data = json.loads((home / COPIES_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def record_copy(*, text: str, max_chars: int, scope: str, home: Path | None = None) -> None:
    """Remember that *text*, rendered with these settings, was copied out."""
    resolved_home = home if home is not None else ensure_home()
    copies = _load_copies(resolved_home)
    copies[f"{scope}:{max_chars}"] = {
        "fingerprint": _fingerprint(text),
        "max_chars": max_chars,
        "scope": scope,
        "copied_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (resolved_home / COPIES_FILE).write_text(
        json.dumps(copies, indent=2, sort_keys=True), encoding="utf-8"
    )


def stale_copies(home: Path | None = None) -> list[tuple[str, int]]:
    """(scope, budget) of every copy that no longer matches the profile.

    Compares the re-rendered text, not the records, so a change to a record
    that never fit that budget does not count.
    """
    resolved_home = home if home is not None else mneva_home()
    stale = set()
    for entry in _load_copies(resolved_home).values():
        try:
            max_chars = int(str(entry["max_chars"]))
            scope = str(entry["scope"])
            fingerprint = str(entry["fingerprint"])
        except (KeyError, TypeError, ValueError):
            continue
        current = render_brief(max_chars=max_chars, scope=scope, home=resolved_home).text
        if _fingerprint(current) != fingerprint:
            stale.add((scope, max_chars))
    return sorted(stale)


def _copy_command(scope: str, max_chars: int) -> str:
    command = "mneva brief --copy"
    if max_chars != DEFAULT_MAX_CHARS:
        command += f" --max-chars {max_chars}"
    if scope != PROFILE_SCOPE:
        command += f" --scope {scope}"
    return command


def stale_notice(home: Path | None = None) -> str | None:
    """One line saying a pasted profile is out of date and how to refresh it."""
    stale = stale_copies(home)
    if not stale:
        return None
    commands = "; ".join(_copy_command(scope, max_chars) for scope, max_chars in stale)
    return (
        "Your profile changed since you last copied it, so the pasted copy is "
        f"out of date. Copy and paste it again: {commands}"
    )


def copy_to_clipboard(text: str) -> None:
    """Copy *text* to the system clipboard."""
    if sys.platform == "win32":
        _copy_windows(text)
        return
    env = None
    if sys.platform == "darwin":
        cmd, data = ["pbcopy"], text.encode("utf-8")
        env = {**os.environ, "LANG": "en_US.UTF-8"}
    else:
        cmd = ["wl-copy"] if shutil.which("wl-copy") else ["xclip", "-selection", "clipboard"]
        data = text.encode("utf-8")
    try:
        subprocess.run(  # noqa: S603
            cmd, input=data, check=True, timeout=_CLIPBOARD_TIMEOUT_SECONDS, env=env
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise ClipboardError(f"could not run {cmd[0]}: {e}") from e


def _copy_windows(text: str) -> None:
    """Write CF_UNICODETEXT through the Win32 API.

    `clip.exe` guesses the input encoding: UTF-16 with a BOM keeps the BOM as
    a visible U+FEFF character, and UTF-16 without one is misread as ANSI for
    short CJK text (a lone 你 came back as two garbage characters). Verified
    by hand on Windows 11, 2026-10-16.
    """
    if sys.platform != "win32":
        raise ClipboardError("Win32 clipboard is only available on Windows")
    import ctypes
    from ctypes import wintypes

    cf_unicodetext = 13
    gmem_moveable = 0x0002
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE

    data = text.encode("utf-16-le") + b"\x00\x00"
    handle = kernel32.GlobalAlloc(gmem_moveable, len(data))
    if not handle:
        raise ClipboardError(f"GlobalAlloc failed ({ctypes.get_last_error()})")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        raise ClipboardError(f"GlobalLock failed ({ctypes.get_last_error()})")
    ctypes.memmove(pointer, data, len(data))
    kernel32.GlobalUnlock(handle)

    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        raise ClipboardError("clipboard is busy (held by another program); try again")
    try:
        user32.EmptyClipboard()
        # On success the system owns the memory; free it only on failure.
        if not user32.SetClipboardData(cf_unicodetext, handle):
            kernel32.GlobalFree(handle)
            raise ClipboardError(f"SetClipboardData failed ({ctypes.get_last_error()})")
    finally:
        user32.CloseClipboard()


@click.command("brief")
@click.option(
    "--max-chars",
    default=DEFAULT_MAX_CHARS,
    show_default=True,
    type=click.IntRange(min=1),
    help="Character budget. Use 1500 for ChatGPT custom instructions.",
)
@click.option("--scope", default=PROFILE_SCOPE, show_default=True, help="Which records form the brief.")
@click.option(
    "--copy",
    "copy_",
    is_flag=True,
    help="Copy to the clipboard instead of printing. mneva remembers the copy and "
    "tells you when your profile changes after it.",
)
def brief_command(max_chars: int, scope: str, copy_: bool) -> None:
    """Print a paste-ready brief of your profile for tools without MCP."""
    result = render_brief(max_chars=max_chars, scope=scope)
    if result.skipped:
        click.echo(
            f"skipped (did not fit in {max_chars} chars): {', '.join(result.skipped)}. "
            "Split long records or raise --max-chars.",
            err=True,
        )
    if not result.included:
        if result.skipped:
            raise click.ClickException("nothing fits; raise --max-chars")
        raise click.ClickException(
            f"no permanent records in scope '{scope}'. Add one with: "
            f"mneva capture --scope {scope} --lifespan permanent --no-git -"
        )
    if copy_:
        try:
            copy_to_clipboard(result.text)
        except ClipboardError as e:
            raise click.ClickException(f"{e}. Run without --copy to print instead.") from e
        click.echo(f"copied {len(result.text)} chars ({len(result.included)} records)", err=True)
        record_copy(text=result.text, max_chars=max_chars, scope=scope)
    else:
        click.echo(result.text)
    notice = stale_notice()
    if notice:
        click.echo(notice, err=True)
