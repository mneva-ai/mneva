"""history.py: the user's own prompts, read from local AI tool history.

Reads files only; nothing here touches the network. Source locations and
record shapes were measured on real installs on 2026-10-18, see
.claude/specs/p1-history-import.spec.md:

- Claude Code keeps every typed prompt in ``history.jsonl`` for months, while
  its full session transcripts are pruned after about 30 days, so only the
  prompt log is read.
- Codex's own prompt log stopped being written in April 2026, so its session
  files are read instead, keeping only user turns.
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CLAUDE_CODE = "claude-code"
CODEX = "codex"
SOURCES = (CLAUDE_CODE, CODEX)

# "ok", "继续" and the like say nothing about the user.
MIN_CHARS = 5
# Longer turns are almost always pasted documents or plans, not the user
# talking about themselves; the head is enough to tell what they were about.
MAX_CHARS = 1500

# Text the tools put into the user's turn. It is not the user speaking.
_INJECTED_PREFIXES = (
    "<task-notification>",
    "<command-name>",
    "<command-message>",
    "<local-command-",
    "[Request interrupted",
    "Caveat:",
    "# AGENTS.md instructions for",
    "<environment_context>",
    "<turn_aborted>",
    "<goal_context>",
    "<subagent_notification>",
    "<user_instructions>",
    "PLEASE IMPLEMENT THIS PLAN",
)
# Codex wraps a request typed in an IDE in editor context; the request itself
# follows the second marker.
_IDE_CONTEXT = "# Context from my IDE setup:"
_IDE_REQUEST = "## My request for Codex:"
_PLACEHOLDERS = re.compile(
    r"<image\b[^>]*>.*?</image>|<image\b[^>]*/?>|\[Image #\d+\]|\[Pasted text #\d+[^\]]*\]", re.S
)
# Redacted before anything leaves the machine. Obvious key shapes only; the
# extraction instructions also tell the model to skip credentials.
_SECRETS = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_-]{30,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.S,
)


@dataclass(frozen=True, slots=True)
class Prompt:
    source: str
    when: datetime  # timezone-aware, UTC
    text: str


def clean(text: str) -> str | None:
    """The user's own words in *text*, or None when there are none worth reading."""
    text = text.strip()
    if text.startswith(_IDE_CONTEXT):
        _, found, request = text.partition(_IDE_REQUEST)
        text = request.strip() if found else ""
    text = _PLACEHOLDERS.sub("", text).strip()
    if text.startswith("/") or text.startswith(_INJECTED_PREFIXES):
        return None
    text = _SECRETS.sub("[redacted]", text)
    if len(text) < MIN_CHARS:
        return None
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + " [truncated]"
    return text


def collect(after: Mapping[str, datetime], *, user_home: Path | None = None) -> list[Prompt]:
    """Prompts newer than each source's watermark, oldest first, repeats dropped."""
    home = user_home if user_home is not None else Path.home()
    claude_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or home / ".claude")
    codex_dir = Path(os.environ.get("CODEX_HOME") or home / ".codex")
    found = [
        *_newer(_claude_code(claude_dir / "history.jsonl"), after.get(CLAUDE_CODE)),
        *_newer(_codex(codex_dir / "sessions"), after.get(CODEX)),
    ]
    found.sort(key=lambda p: p.when)
    seen: set[str] = set()
    unique: list[Prompt] = []
    for prompt in found:
        if prompt.text not in seen:
            seen.add(prompt.text)
            unique.append(prompt)
    return unique


def _newer(prompts: Iterator[Prompt], after: datetime | None) -> Iterator[Prompt]:
    return (p for p in prompts if after is None or p.when > after)


def _json_lines(path: Path) -> Iterator[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            yield obj


def _claude_code(path: Path) -> Iterator[Prompt]:
    for row in _json_lines(path):
        # Pasted documents live in `pastedContents` and are left out on purpose.
        display, stamp = row.get("display"), row.get("timestamp")
        if not isinstance(display, str) or not isinstance(stamp, int | float):
            continue
        text = clean(display)
        if text is not None:
            yield Prompt(CLAUDE_CODE, datetime.fromtimestamp(stamp / 1000, UTC), text)


def _codex(sessions: Path) -> Iterator[Prompt]:
    if not sessions.is_dir():
        return
    for path in sorted(sessions.rglob("*.jsonl")):
        for row in _json_lines(path):
            payload = row.get("payload")
            if (
                row.get("type") != "response_item"
                or not isinstance(payload, dict)
                or payload.get("type") != "message"
                or payload.get("role") != "user"
            ):
                continue
            when = _parse_time(row.get("timestamp"))
            if when is None:
                continue
            # One turn can hold several blocks, e.g. an image and the question
            # about it; each is judged on its own.
            for block in payload.get("content") or []:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    text = clean(block["text"])
                    if text is not None:
                        yield Prompt(CODEX, when, text)


def _parse_time(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        when = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=UTC)
