"""learn_auto.py: run ``mneva learn`` by itself about once a day.

mneva's MCP server starts with every Claude Code or Codex session, so it is
the one place mneva runs daily with no scheduler and nothing to set up. On
start it calls maybe_start(), which launches one background run when the last
finished run is older than INTERVAL. The run only proposes: the proposal
reaches the user through replay_context (pending_notice), and the profile
changes only when they accept it with ``mneva learn --accept``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import click

from mneva import learn
from mneva.brief import PROFILE_SCOPE
from mneva.paths import ensure_home
from mneva.store import iter_records

AUTO_FILE = "learn-auto.json"
LOCK_FILE = "learn.lock"
LOG_FILE = "learn.log"
# Set to "0" to turn the daily run off; the launched run also carries it, so
# nothing it starts can launch another.
OFF_VAR = "MNEVA_LEARN_AUTO"
# Under 24 hours, so a session opened a little earlier than yesterday's still runs.
INTERVAL = timedelta(hours=20)
# A run ended together with its session leaves its lock; after this it is retried.
LOCK_STALE = timedelta(hours=1)
# About three extract calls. A day of prompts fits; `mneva learn --all` reads everything.
MAX_CHARS = 120_000
# Fewer than this is not worth two model calls; they wait for the next run.
MIN_PROMPTS = 20
_LOG_MAX_BYTES = 1_048_576


def _finished(home: Path) -> datetime | None:
    raw = (learn._read_json(home / AUTO_FILE) or {}).get("finished")
    try:
        return datetime.fromisoformat(raw) if isinstance(raw, str) else None
    except ValueError:
        return None


def record_finish(home: Path, when: datetime, result: str) -> None:
    learn._write_json(home / AUTO_FILE, {"finished": when.isoformat(), "result": result})


def _lock_held(home: Path, now: datetime) -> bool:
    try:
        mtime = (home / LOCK_FILE).stat().st_mtime
    except FileNotFoundError:
        return False
    return now - datetime.fromtimestamp(mtime, UTC) < LOCK_STALE


def should_start(home: Path, now: datetime) -> bool:
    if os.environ.get(OFF_VAR) == "0" or shutil.which("claude") is None:
        return False
    # A pending proposal waits for the user; a second run would have to merge into it.
    if (home / learn.PROPOSAL_FILE).exists() or _lock_held(home, now):
        return False
    finished = _finished(home)
    if finished is not None and now - finished < INTERVAL:
        return False
    # No profile yet: nothing to edit, and a fresh install should not send its
    # whole history out before the user has written anything.
    return any(r.scope == PROFILE_SCOPE for r in iter_records(home=home))


def _detached() -> dict[str, Any]:
    if sys.platform == "win32":
        # Not DETACHED_PROCESS: with no console at all, claude.CMD opens a visible one.
        return {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def maybe_start(home: Path) -> None:
    """Launch one background learn run if one is due. Never raises: the server must start regardless."""
    try:
        if not should_start(home, datetime.now(UTC)):
            return
        log_path = home / LOG_FILE
        mode = "w" if log_path.exists() and log_path.stat().st_size > _LOG_MAX_BYTES else "a"
        with log_path.open(mode, encoding="utf-8") as log:
            subprocess.Popen(  # noqa: S603
                [sys.executable, "-m", "mneva.learn_auto"],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=home,
                env={**os.environ, OFF_VAR: "0"},
                **_detached(),
            )
    except Exception:  # noqa: S110 - learning is optional; the server is not
        pass


def _take_lock(home: Path, now: datetime) -> bool:
    if _lock_held(home, now):
        return False
    path = home / LOCK_FILE
    path.unlink(missing_ok=True)  # stale
    try:
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        return False
    return True


def run(home: Path) -> None:
    """One background run: propose edits from new prompts, on the login only."""
    started = datetime.now(UTC)
    if not _take_lock(home, started):
        return
    try:
        click.echo(f"[{started:%Y-%m-%d %H:%M} UTC] mneva learn, automatic run")
        try:
            proposal = learn.new_proposal(
                home,
                backend="claude-code",
                from_start=False,
                max_chars=MAX_CHARS,
                min_prompts=MIN_PROMPTS,
                allow_api_key=False,
            )
            result = f"proposed {len(proposal['edits'])} changes" if proposal else "no proposal"
        except click.ClickException as exc:
            result = f"failed: {exc.message}"
        click.echo(result)
        record_finish(home, datetime.now(UTC), result)
    finally:
        (home / LOCK_FILE).unlink(missing_ok=True)


def pending_notice(home: Path) -> str | None:
    """A line for the model to pass on when a proposal waits for the user."""
    count = len((learn._read_json(home / learn.PROPOSAL_FILE) or {}).get("edits") or [])
    if not count:
        return None
    changes = "1 proposed change" if count == 1 else f"{count} proposed changes"
    return (
        f"mneva notice: mneva learned {changes} to this profile from the user's recent prompts. "
        "Tell the user in one short line, in their language, before your answer: they can review them with "
        "`mneva learn` (in Claude Code, type `! mneva learn`), then apply them with `mneva learn --accept all` "
        "or by number, or drop them with `mneva learn --discard`. Nothing changes until they accept."
    )


if __name__ == "__main__":  # pragma: no cover
    run(ensure_home())
