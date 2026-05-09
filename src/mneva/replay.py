"""replay.py — shared logic for `mneva replay` CLI and GET /replay HTTP endpoint."""
from __future__ import annotations

import importlib.resources
from pathlib import Path

from mneva.paths import ensure_home
from mneva.store import iter_records

# Maps tool identifier -> template filename inside mneva/templates/
TEMPLATE_FILES: dict[str, str] = {
    "claude-code": "claude-code.reference.md",
    "cursor": "cursor.rules.md",
    "codex": "codex.agents.md",
}

VALID_TOOLS: frozenset[str] = frozenset(TEMPLATE_FILES)


def _load_template(tool: str) -> str:
    """Load template text via importlib.resources (works inside wheel)."""
    filename = TEMPLATE_FILES[tool]
    pkg = importlib.resources.files("mneva.templates")
    return pkg.joinpath(filename).read_text("utf-8")


def _strip_frontmatter(text: str) -> str:
    """Strip YAML frontmatter block (--- ... ---) from the top of text if present."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        return text
    # Find closing ---
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            # Return everything after the closing delimiter line
            return "".join(lines[i + 1 :]).lstrip("\n")
    return text  # no closing delimiter found -- return unchanged


def render_replay(
    tool: str,
    scope: str | None = None,
    home: Path | None = None,
) -> str:
    """Render the context replay block for *tool*, optionally filtered by *scope*.

    Returns the assembled string (template body + captured permanent records).
    Raises ValueError if *tool* is not a recognised tool identifier.
    """
    if tool not in TEMPLATE_FILES:
        valid = ", ".join(sorted(VALID_TOOLS))
        raise ValueError(f"unknown tool: {tool!r}  (valid: {valid})")

    resolved_home = home if home is not None else ensure_home()

    template_body = _strip_frontmatter(_load_template(tool))

    # Collect permanent records, optionally filtered by scope
    records = [
        r
        for r in iter_records(home=resolved_home)
        if r.lifespan == "permanent" and (scope is None or r.scope == scope)
    ]

    parts: list[str] = [template_body.rstrip()]
    parts.append("\n\n## Captured records\n")

    if not records:
        if scope is not None:
            parts.append(f"_No captured records for scope `{scope}`._")
        else:
            parts.append("_No captured permanent records._")
    else:
        for r in records:
            tool_source = r.source or r.tool
            parts.append(f"\n### {r.scope} · {r.id} · {r.lifespan} · {tool_source}")
            parts.append(r.body)

    return "\n".join(parts) + "\n"
