"""`mneva diagnose [--share]` — opt-in, zero-content observability report.

Locked by /plan-ceo-review F1. mneva ships with no passive telemetry: no
auto-send, no callbacks, no opt-in toggle at install. Users who want to help
the maintainer (or who want to attach a debug bundle to a bug report) run
``mneva diagnose --share`` and paste the output manually.

Hard rules
----------
1. Zero record content. We never read or print bodies, ids, scopes-from-data
   beyond aggregate counts.
2. Stdout only. We do not call ``mneva.org`` or any other host.
3. ``--share`` is a verbosity flag, not a sender.
"""
from __future__ import annotations

import json
import os
import platform
import sys
from collections import Counter
from pathlib import Path

from mneva import __version__
from mneva.indexer import Indexer
from mneva.paths import mneva_home
from mneva.store import iter_records

_ATTRIBUTION_LOG = ".mcp-attribution.log"

_BACKEND_ENV_VARS: tuple[tuple[str, str], ...] = (
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai", "OPENAI_API_KEY"),
    ("google", "GOOGLE_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
)


def _home_state(home: Path) -> str:
    if not home.exists():
        return "missing (mneva-mcp will create on first run)"
    try:
        probe = home / ".diagnose-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return f"{home} (writable)"
    except OSError:
        return f"{home} (NOT writable)"


def _record_counts(home: Path) -> tuple[int, Counter[str]]:
    if not (home / "store").exists():
        return 0, Counter()
    counts: Counter[str] = Counter()
    total = 0
    for record in iter_records(home=home):
        total += 1
        counts[record.lifespan] += 1
    return total, counts


def _backends_configured() -> list[str]:
    """Return list of backends with a non-empty key set. Values are NOT read."""
    return [name for name, env in _BACKEND_ENV_VARS if os.environ.get(env)]


def _attribution_counts(home: Path) -> tuple[Counter[str], str | None]:
    """Parse the MCP attribution log. Returns (per-client counts, last ts)."""
    path = home / _ATTRIBUTION_LOG
    if not path.exists():
        return Counter(), None
    clients: Counter[str] = Counter()
    last_ts: str | None = None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            client = str(entry.get("client", "unknown"))
            clients[client] += 1
            ts = entry.get("ts")
            if isinstance(ts, str):
                last_ts = ts
    except OSError:
        pass
    return clients, last_ts


def _index_mode(home: Path) -> str:
    db = home / "mneva.sqlite"
    if not db.exists():
        return "not initialized"
    try:
        return Indexer(db).mode
    except Exception:
        return "unavailable"


def render_diagnose(share: bool = False) -> str:
    """Build the diagnostic report. Returns the full text to print."""
    home = mneva_home()
    total, by_lifespan = _record_counts(home)
    backends = _backends_configured()
    clients, last_ts = _attribution_counts(home)

    lines: list[str] = []
    lines.append(f"mneva diagnose v{__version__}")
    lines.append("=" * 40)
    lines.append(f"platform: {platform.system()}-{platform.release()}-{platform.machine()}")
    lines.append(f"python: {sys.version.split()[0]} ({platform.python_implementation()})")
    lines.append(f"mneva home: {_home_state(home)}")
    lines.append(f"index mode: {_index_mode(home)}")
    if by_lifespan:
        breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(by_lifespan.items()))
        lines.append(f"records: {total} ({breakdown})")
    else:
        lines.append(f"records: {total}")
    lines.append(
        f"backends configured: {', '.join(backends) if backends else 'none'}"
    )
    if clients:
        client_summary = ", ".join(
            f"{name} ({n})" for name, n in clients.most_common()
        )
        lines.append(f"mcp clients seen: {client_summary}")
    else:
        lines.append("mcp clients seen: none")
    lines.append(f"last mcp call: {last_ts or 'never'}")

    if share:
        lines.append("")
        lines.append("This report contains NO record content.")
        lines.append("To share with the mneva maintainer:")
        lines.append("  copy the output above and paste in WeChat / email / GitHub issue.")
    return "\n".join(lines) + "\n"
