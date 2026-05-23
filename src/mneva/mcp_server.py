"""MCP server entry point — exposes mneva memory primitives over stdio.

This module is the v0.2 product surface. Run it via the ``mneva-mcp`` console
script (installed by ``uvx mneva``) and wire the resulting process into any
MCP-capable AI client (Claude Desktop, Claude Code, Cursor, Windsurf, Cline,
Continue, ChatGPT Desktop in Developer Mode).

Design notes
------------
* No new business logic. Every tool is a thin adapter around an existing
  ``mneva`` primitive (``store.write_record``, ``Indexer.search``, etc).
* Tools return ``dict`` payloads with a human-readable ``summary`` field. The
  AI client reads ``summary`` aloud, so the user sees "Captured: ..." instead
  of an opaque id.
* Auto-init on first run. ``main()`` calls ``ensure_home()`` and creates a
  fresh ``config.json`` if missing, so the user does not have to run
  ``mneva init`` before wiring the MCP server.
* Client attribution via ``MNEVA_MCP_CLIENT`` env var, set per client in
  each client's MCP config block. Falls back to "mcp" if unset; logs a
  one-time stderr WARNING so the user can fix the config.
* Per-call attribution log appended to ``~/.mneva/.mcp-attribution.log``
  (1 MB cap, monthly rotation). Counts only, zero record content. Read by
  ``mneva diagnose`` for opt-in usage reporting.
* SQLite contention across concurrent ``mneva-mcp`` processes is handled by
  the WAL + busy_timeout PRAGMAs set in ``Indexer.__init__``.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from mneva.indexer import Indexer
from mneva.paths import ensure_home, mneva_home
from mneva.replay import VALID_TOOLS, render_replay
from mneva.store import (
    Record,
    forget_record,
    make_record_id,
    read_record,
    write_record,
)

mcp: FastMCP = FastMCP("mneva")

_VALID_LIFESPANS: frozenset[str] = frozenset({"transient", "permanent"})
_ATTRIBUTION_LOG = ".mcp-attribution.log"
_ATTRIBUTION_MAX_BYTES = 1_048_576  # 1 MB cap before rotation

_indexer: Indexer | None = None


def _get_indexer() -> Indexer:
    """Lazy, module-level Indexer singleton. Reused across all tool calls."""
    global _indexer
    if _indexer is None:
        home = ensure_home()
        _indexer = Indexer(home / "mneva.sqlite")
    return _indexer


def _client_id() -> str:
    """Resolve the calling MCP client name. Falls back to 'mcp' when unset."""
    name = os.environ.get("MNEVA_MCP_CLIENT", "").strip()
    return name or "mcp"


def _log_attribution(action: str) -> None:
    """Append a one-line attribution entry. Best-effort; never raises.

    Format: ``{"ts": "...", "client": "...", "action": "..."}`` JSONL.
    Rotates the file by truncation when it exceeds ``_ATTRIBUTION_MAX_BYTES``.
    """
    try:
        home = mneva_home()
        path = home / _ATTRIBUTION_LOG
        if path.exists() and path.stat().st_size > _ATTRIBUTION_MAX_BYTES:
            path.unlink()
        entry = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "client": _client_id(),
            "action": action,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # Attribution is opt-in observability, not load-bearing. Swallow.
        pass


def _truncate(text: str, limit: int = 80) -> str:
    """Render a single-line preview of *text* for tool summaries."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


@mcp.tool()
def capture_memory(
    scope: str,
    body: str,
    lifespan: str = "transient",
    source: str | None = None,
) -> dict[str, Any]:
    """Capture a memory record into mneva.

    Args:
        scope: Logical bucket (e.g. project name) the record belongs to.
        body: Free-form text of the memory.
        lifespan: "transient" (default, ephemeral) or "permanent" (long-lived).
        source: Optional short note about where this memory came from.

    Returns:
        Dict with ``id``, ``summary``, and ``record`` keys. ``summary`` is a
        human-readable line the AI client should speak back to the user so the
        capture is visible, not silent.
    """
    if not scope or not scope.strip():
        return {
            "error": "scope is required",
            "summary": "Capture refused: scope is required.",
        }
    if not body or not body.strip():
        return {
            "error": "body is empty",
            "summary": "Capture refused: body is empty.",
        }
    if lifespan not in _VALID_LIFESPANS:
        return {
            "error": f"invalid lifespan {lifespan!r}",
            "summary": (
                f"Capture refused: lifespan must be one of "
                f"{sorted(_VALID_LIFESPANS)}, got {lifespan!r}."
            ),
        }

    home = ensure_home()
    record = Record(
        id=make_record_id(scope, body),
        scope=scope,
        lifespan=lifespan,
        tool=_client_id(),
        body=body,
        source=source,
    )
    try:
        write_record(record, home=home)
    except FileExistsError:
        # Time-keyed ids make this practically impossible; if it does happen,
        # surface a friendly summary and let the client retry.
        return {
            "error": "record id collision",
            "summary": "Capture refused: rare id collision. Retry the request.",
        }
    _get_indexer().add(record)
    _log_attribution("capture")
    return {
        "id": record.id,
        "summary": f"Captured ({lifespan}, scope={scope}): {_truncate(body)}",
        "record": record.to_dict(),
    }


@mcp.tool()
def search_memory(
    query: str,
    scope: str | None = None,
    lifespan: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Search mneva memories using hybrid BM25 + optional sqlite-vec ranking.

    Args:
        query: Free-form search string.
        scope: Optional filter — restrict to this scope only.
        lifespan: Optional filter — "transient" or "permanent".
        top_k: Maximum number of hits to return (1..50; default 10).

    Returns:
        Dict with ``hits`` (list of record dicts) and ``summary`` (human line).
    """
    if not query or not query.strip():
        return {
            "hits": [],
            "summary": "Search refused: query is empty.",
        }
    if lifespan is not None and lifespan not in _VALID_LIFESPANS:
        return {
            "hits": [],
            "summary": (
                f"Search refused: lifespan must be one of "
                f"{sorted(_VALID_LIFESPANS)}, got {lifespan!r}."
            ),
        }
    top_k = max(1, min(top_k, 50))
    records = _get_indexer().search(query, scope=scope, lifespan=lifespan, k=top_k)
    _log_attribution("search")
    if not records:
        scope_note = f" in scope `{scope}`" if scope else ""
        return {
            "hits": [],
            "summary": f"No memories matched {query!r}{scope_note}.",
        }
    return {
        "hits": [r.to_dict() for r in records],
        "summary": (
            f"Found {len(records)} memory match{'es' if len(records) != 1 else ''}"
            f" for {query!r}: {_truncate(records[0].body)}"
        ),
    }


@mcp.tool()
def forget_memory(record_id: str) -> dict[str, Any]:
    """Delete a memory by id. The id is what ``capture_memory`` returned.

    Args:
        record_id: The 16-hex-char record id (returned by capture_memory or
            visible in search hits).

    Returns:
        Dict with ``ok`` (bool) and ``summary`` (human line).
    """
    if not record_id or not record_id.strip():
        return {
            "ok": False,
            "summary": "Forget refused: record_id is required.",
        }
    home = ensure_home()
    removed = forget_record(record_id, home=home)
    if not removed:
        return {
            "ok": False,
            "summary": f"No memory found with id {record_id!r}.",
        }
    _get_indexer().remove(record_id)
    _log_attribution("forget")
    return {
        "ok": True,
        "summary": f"Forgot memory {record_id}.",
    }


@mcp.tool()
def list_recent_memories(
    scope: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List the most recently captured memories, newest first.

    Args:
        scope: Optional filter — restrict to this scope only.
        limit: Max number of memories to return (1..50; default 20).

    Returns:
        Dict with ``memories`` (list of record dicts) and ``summary``.
    """
    limit = max(1, min(limit, 50))
    home = ensure_home()
    store_dir = home / "store"
    if not store_dir.exists():
        return {
            "memories": [],
            "summary": "No memories captured yet.",
        }

    # mtime sort. Cheap for <10k records; v0.3 may add an indexer-level
    # recency cursor if a user reports slowness.
    files = sorted(
        store_dir.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    records: list[Record] = []
    for path in files:
        try:
            record = read_record(path.stem, home=home)
        except (OSError, KeyError, ValueError, TypeError):
            # Malformed or partially-written record — skip silently. Listing
            # is best-effort; full integrity check belongs to a future
            # `mneva check` command.
            continue
        if scope is not None and record.scope != scope:
            continue
        records.append(record)
        if len(records) >= limit:
            break
    _log_attribution("list_recent")
    if not records:
        scope_note = f" in scope `{scope}`" if scope else ""
        return {
            "memories": [],
            "summary": f"No memories{scope_note} yet.",
        }
    return {
        "memories": [r.to_dict() for r in records],
        "summary": (
            f"Returning {len(records)} most-recent "
            f"memor{'ies' if len(records) != 1 else 'y'}"
            f"{' from scope ' + repr(scope) if scope else ''}."
        ),
    }


@mcp.tool()
def replay_context(
    tool: str = "claude-code",
    scope: str | None = None,
) -> str:
    """Return a bootstrap context block for a specific AI tool, as Markdown.

    Wraps the existing ``mneva replay`` rendering used by the HTTP API. The
    output is a single Markdown string suitable for pasting directly into a
    new chat session as opening context.

    Args:
        tool: Tool identifier. Valid values: "claude-code", "cursor", "codex".
        scope: Optional scope filter. ``None`` includes records from all scopes.

    Returns:
        Markdown string. The MCP client should render this as a code block or
        attached file in the chat.
    """
    if tool not in VALID_TOOLS:
        valid = ", ".join(sorted(VALID_TOOLS))
        return f"replay_context error: unknown tool {tool!r}. Valid: {valid}."
    home = ensure_home()
    _log_attribution("replay")
    return render_replay(tool, scope=scope, home=home)


@mcp.tool()
def get_status() -> dict[str, Any]:
    """Return mneva's current state — record count, index mode, paths.

    Useful as a health probe and as the first call an AI client makes to
    confirm mneva is wired up.
    """
    home = ensure_home()
    indexer_status = _get_indexer().status()
    count = int(indexer_status.get("count", 0))
    mode = str(indexer_status.get("mode", "bm25"))
    _log_attribution("status")
    return {
        "home": str(home),
        "mode": mode,
        "count": count,
        "client": _client_id(),
        "summary": (
            f"mneva is wired up. {count} memor{'ies' if count != 1 else 'y'} stored"
            f" (index mode: {mode}, home: {home})."
        ),
    }


def _auto_init() -> None:
    """Create ~/.mneva/ and a default config.json if missing.

    Locked by /plan-eng-review D1: "config snippet, restart, done" — users
    paste the MCP config into Claude Desktop without first running
    ``mneva init``, so the server must materialize its own state on first
    run. Reuses the same primitives the CLI ``init`` command uses, so
    init behavior stays single-sourced.
    """
    from mneva.config import Config, generate_token, save_config

    home = ensure_home()
    if not (home / "config.json").exists():
        save_config(Config(token=generate_token()), home)


def main() -> None:
    """Console-script entry point: ``mneva-mcp``.

    Performs auto-init, validates the attribution env var, then hands control
    to FastMCP. Startup failures are written to stderr in a single
    machine-readable line so MCP hosts (Claude Desktop, Cursor, ...) can
    surface a diagnosable error in their log.
    """
    try:
        _auto_init()
    except OSError as e:
        # Disk full, permission denied, exotic FS errors. Locked by F3.
        sys.stderr.write(
            f"mneva-mcp: startup failed: {type(e).__name__}: {e}\n"
        )
        sys.stderr.write(
            "mneva-mcp: see your MCP host's log for full output.\n"
        )
        sys.exit(2)

    # One-time WARNING if attribution env var is unset. Users who copy a
    # config snippet without the ``env`` block end up with everything tagged
    # "mcp" and lose per-client attribution.
    if not os.environ.get("MNEVA_MCP_CLIENT", "").strip():
        sys.stderr.write(
            "mneva-mcp: WARNING: MNEVA_MCP_CLIENT env var is not set. "
            "Memories will be tagged 'mcp'. Add "
            '`"env": {"MNEVA_MCP_CLIENT": "claude-desktop"}` (or your client '
            "name) to the MCP config block to enable per-client attribution.\n"
        )

    mcp.run()


__all__ = ["main", "mcp"]


# Allow `python -m mneva.mcp_server` so tests can subprocess-spawn it.
if __name__ == "__main__":  # pragma: no cover
    main()
