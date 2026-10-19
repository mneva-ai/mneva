"""learn.py: keep the profile current from what the user typed into their AI tools.

``mneva learn`` reads new prompts from local Claude Code and Codex history
(``history.py``), extracts dated facts about the user chunk by chunk on a
cheaper model, then asks a stronger model for edits to the existing profile
records. Edits are saved as a proposal and reach the store only when the user
accepts them: one wrong fact would otherwise be inserted into every AI chat.
Spec: .claude/specs/p1-history-import.spec.md.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from mneva import history
from mneva.brief import PROFILE_SCOPE
from mneva.distill import chunk_text
from mneva.indexer import Indexer
from mneva.paths import ensure_home
from mneva.providers import Provider, ProviderError, get_provider
from mneva.store import (
    Record,
    forget_record,
    iter_records,
    make_record_id,
    read_record,
    write_record,
)
from mneva.vault import mirror_if_configured

# Bookkeeping, not memory: deleting either file loses no record.
STATE_FILE = "learn-state.json"
PROPOSAL_FILE = "learn-proposal.json"

EXTRACT_MODEL = "sonnet"  # many calls over raw prompts
MERGE_MODEL = "opus"  # one call that decides what the profile says
_CHUNK_CHARS = 40_000
_MAX_TOKENS = 8000
# The brief packs whole records into 4,000 chars and drops what does not fit,
# so the profile stays well under that.
PROFILE_BUDGET_CHARS = 3000
PROFILE_MARKER = "=== PROFILE ==="
_OPS = ("update", "add", "remove")
# Both steps carry this: the profile is inserted into every chat, in every
# tool, so what one step lets through the other must still stop.
_NEVER = (
    "Never include passwords, keys, health, money, immigration or other legal matters, or anything about other "
    "people: no names of family, friends, coworkers or a client's staff; say \"a client\" or \"the product lead\"."
)

_EXTRACT_PROMPT = """Below are prompts one person typed into AI tools, oldest first, each with its date and tool.
Extract durable facts about this person that would help any AI assistant work with them: who they are (role,
background, languages), how they want AI to work with them (style, format, rules they keep repeating), the tools
and services they use, their projects and each project's current state, their priorities and decisions.

Rules:
- Only facts the prompts support. Do not guess.
- One sentence per fact, starting with the date it was last seen (YYYY-MM-DD), in the language the person writes in.
- Skip one-off task details, code and error messages.
- {never}
- A preference repeated many times is one fact, dated when it was last seen.
- At most 40 facts.

Answer with JSON only: {{"facts": ["YYYY-MM-DD: ...", ...]}}

=== PROMPTS ===
"""

_MERGE_PROMPT = """You maintain one person's profile: a few Markdown sections inserted at the start of their AI chats.
Below are the current sections, each with its id, and facts learned from what the person typed, oldest first.

Propose edits so the profile is accurate as of the newest fact:
- "update" a section that is out of date or misses something important; give the full new body and keep its heading.
- "add" a section only for a kind of information no section covers.
- "remove" a section only if all of it is obsolete.
Newer facts win over older ones and over the current text. Finished or abandoned work leaves "what I am doing".
Each project there gets one short entry: its goal, current phase and next milestone. No individual tasks, tickets
or UI changes; they are stale within a week.
A rule that applies to one project or client goes inside that project's entry, never into a general section.
{never} Take such details out if the current text has them.
Keep the person's language, voice and heading style. Add nothing the facts do not support. Leave sections that need
no change out of the answer. The whole profile must stay under {budget} characters.

Answer with JSON only:
{{"edits": [{{"op": "update" | "add" | "remove", "id": "<section id, for update and remove>",
"body": "<full Markdown, for update and add>", "reason": "<one short line in the person's language>"}}]}}

"""


@dataclass(frozen=True, slots=True)
class Edit:
    op: str
    id: str | None
    body: str | None
    reason: str


def make_providers(backend: str, *, allow_api_key: bool = True) -> tuple[Provider, Provider]:
    """(extractor, merger). Claude Code needs no key; the others read theirs from the env."""
    if backend == "claude-code":
        from mneva.providers.claude_cli import ClaudeCliProvider

        return (
            ClaudeCliProvider(model=EXTRACT_MODEL, allow_api_key=allow_api_key),
            ClaudeCliProvider(model=MERGE_MODEL, allow_api_key=allow_api_key),
        )
    provider = get_provider(backend)
    return provider, provider


def _json_object(raw: str) -> dict[str, Any]:
    start, end = raw.find("{"), raw.rfind("}")
    try:
        value = json.loads(raw[start : end + 1]) if start >= 0 else None
    except ValueError:
        value = None
    if not isinstance(value, dict):
        raise ProviderError(f"model did not answer with JSON: {raw[:200]!r}")
    return value


def extract_facts(
    provider: Provider, prompts: list[history.Prompt], *, progress: Any = None
) -> list[str]:
    text = "\n\n".join(f"[{p.when:%Y-%m-%d} {p.source}] {p.text}" for p in prompts)
    chunks = chunk_text(text, _CHUNK_CHARS)
    facts: list[str] = []
    for n, chunk in enumerate(chunks, 1):
        if progress is not None:
            progress(f"  extracting facts: part {n} of {len(chunks)}")
        found = _json_object(provider.complete(_EXTRACT_PROMPT.format(never=_NEVER) + chunk, max_tokens=_MAX_TOKENS)).get("facts")
        facts.extend(f.strip() for f in found or [] if isinstance(f, str) and f.strip())
    return facts


def propose_edits(provider: Provider, records: list[Record], facts: list[str]) -> list[Edit]:
    sections = "\n\n".join(f"[{r.id}]\n{r.body.strip()}" for r in records)
    prompt = (
        _MERGE_PROMPT.format(budget=PROFILE_BUDGET_CHARS, never=_NEVER)
        + f"{PROFILE_MARKER}\n{sections}\n\n=== FACTS ===\n"
        + "\n".join(facts)
    )
    raw_edits = _json_object(provider.complete(prompt, max_tokens=_MAX_TOKENS)).get("edits") or []
    current = {r.id: r.body.strip() for r in records}
    edits: list[Edit] = []
    for raw in raw_edits:
        if not isinstance(raw, dict) or raw.get("op") not in _OPS:
            continue
        op, raw_id, raw_body = raw["op"], raw.get("id"), raw.get("body")
        rid = raw_id if isinstance(raw_id, str) and raw_id in current else None
        body = raw_body.strip() if isinstance(raw_body, str) else ""
        reason = str(raw.get("reason") or "").strip()
        if op == "remove":
            if rid is not None:
                edits.append(Edit(op=op, id=rid, body=None, reason=reason))
        elif op == "add":
            if body:
                edits.append(Edit(op=op, id=None, body=body, reason=reason))
        elif rid is not None and body and body != current[rid]:
            edits.append(Edit(op=op, id=rid, body=body, reason=reason))
    return edits


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_state(home: Path) -> dict[str, datetime]:
    state: dict[str, datetime] = {}
    for source, raw in (_read_json(home / STATE_FILE) or {}).items():
        try:
            state[source] = datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            continue
    return state


def apply_edits(edits: list[Edit], home: Path) -> list[str]:
    """Write accepted edits through the normal store path; returns one line per edit."""
    done: list[str] = []
    with Indexer(home / "mneva.sqlite") as idx:
        for edit in edits:
            if edit.op == "add" and edit.body:
                record = Record(
                    id=make_record_id(PROFILE_SCOPE, edit.body),
                    scope=PROFILE_SCOPE,
                    lifespan="permanent",
                    tool="mneva-learn",
                    body=edit.body,
                    source="mneva learn",
                )
                write_record(record, home=home)
            elif edit.id is None:
                continue
            elif edit.op == "remove":
                forget_record(edit.id, home=home)
                idx.remove(edit.id)
                done.append(f"removed {edit.id}")
                continue
            else:
                try:
                    # Same id: the brief, the index and the vault all key on it.
                    record = replace(read_record(edit.id, home=home), body=edit.body or "")
                except FileNotFoundError:
                    done.append(f"skipped {edit.id}: no longer exists")
                    continue
                write_record(record, home=home, overwrite=True)
            idx.add(record)
            mirror_if_configured(record, home)
            done.append(f"{'added' if edit.op == 'add' else 'updated'} {record.id}")
    return done


def _indent(text: str) -> str:
    return "\n".join(f"     {line}" for line in text.strip().splitlines())


def _show(edits: list[Edit], home: Path) -> None:
    click.echo(f"\nProposed changes to your profile ({len(edits)}):")
    for n, edit in enumerate(edits, 1):
        click.echo(f"\n{n}. {edit.op} {edit.id or ''}  ({edit.reason})")
        if edit.op != "add" and edit.id:
            try:
                click.echo("   now:\n" + _indent(read_record(edit.id, home=home).body))
            except FileNotFoundError:
                click.echo("   now: (record no longer exists)")
        if edit.body:
            click.echo("   proposed:\n" + _indent(edit.body))


def _pick(choice: str, count: int) -> list[int]:
    choice = choice.strip().lower()
    if choice == "all":
        return list(range(count))
    if choice in ("", "none"):
        return []
    try:
        picked = sorted({int(part) - 1 for part in choice.replace(",", " ").split()})
    except ValueError as exc:
        raise click.ClickException(f"--accept takes numbers like 1,3 or 'all', not {choice!r}") from exc
    if any(n < 0 or n >= count for n in picked):
        raise click.ClickException(f"--accept: numbers must be between 1 and {count}")
    return picked


def _finish(proposal_path: Path, edits: list[Edit], picked: list[int], home: Path) -> None:
    for line in apply_edits([edits[n] for n in picked], home):
        click.echo(f"  {line}")
    proposal_path.unlink(missing_ok=True)
    click.echo(f"Applied {len(picked)} of {len(edits)} changes. New chats get the updated profile.")


@click.command("learn")
@click.option(
    "--backend",
    default="claude-code",
    show_default=True,
    type=click.Choice(["claude-code", "anthropic", "openai", "google", "openrouter"]),
    help="Who extracts the facts. claude-code runs your local Claude Code and needs no API key.",
)
@click.option("--all", "from_start", is_flag=True, help="Read all history again, not just what is new.")
@click.option("--accept", help="Apply the pending proposal's changes by number (1,3) or 'all'.")
@click.option("--discard", is_flag=True, help="Drop the pending proposal without applying it.")
def learn_command(backend: str, from_start: bool, accept: str | None, discard: bool) -> None:
    """Update your profile from what you typed into Claude Code and Codex."""
    home = ensure_home()
    proposal_path = home / PROPOSAL_FILE
    proposal = _read_json(proposal_path)
    if discard or accept is not None:
        if proposal is None:
            raise click.ClickException("no pending proposal; run `mneva learn` first")
        if discard:
            proposal_path.unlink(missing_ok=True)
            click.echo("Proposal discarded.")
            return
    if proposal is None:
        proposal = new_proposal(home, backend=backend, from_start=from_start)
        if proposal is None:
            return
    edits = [Edit(**e) for e in proposal.get("edits", [])]
    if accept is not None:
        _finish(proposal_path, edits, _pick(accept, len(edits)), home)
        return
    _show(edits, home)
    # Ask only when a person is at both ends: a run whose output goes to a
    # file can still inherit a console stdin, and the prompt then reads EOF.
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            choice = click.prompt("\nAccept which? (numbers like 1 3, 'all' or 'none')", default="none")
        except click.Abort:
            choice = None
        if choice is not None:
            _finish(proposal_path, edits, _pick(choice, len(edits)), home)
            return
    example = ",".join(str(n) for n in range(1, min(len(edits), 2) + 1))
    click.echo(
        f"\nThe proposal is saved. To apply: mneva learn --accept {example} (or all). "
        "To drop: mneva learn --discard"
    )


def _newest(prompts: list[history.Prompt], max_chars: int) -> list[history.Prompt]:
    kept: list[history.Prompt] = []
    total = 0
    for prompt in reversed(prompts):
        total += len(prompt.text)
        if total > max_chars and kept:
            break
        kept.append(prompt)
    return kept[::-1]


def new_proposal(
    home: Path,
    *,
    backend: str,
    from_start: bool,
    max_chars: int | None = None,
    min_prompts: int = 1,
    allow_api_key: bool = True,
) -> dict[str, Any] | None:
    """Read new prompts, ask the models, save and return the proposal (None if no edits).

    Below *min_prompts* nothing is sent and the watermark stays, so those
    prompts count toward the next run. *max_chars* keeps only the newest
    prompts; the older ones are passed over for good.
    """
    state = {} if from_start else _load_state(home)
    prompts = history.collect(state)
    if not prompts:
        click.echo("Nothing new to learn from since the last run.")
        return None
    if len(prompts) < min_prompts:
        click.echo(f"Only {len(prompts)} new prompts; waiting for {min_prompts}.")
        return None
    if max_chars is not None:
        prompts = _newest(prompts, max_chars)
    counts = {s: sum(p.source == s for p in prompts) for s in history.SOURCES}
    click.echo(
        "Read "
        + ", ".join(f"{n} prompts from {s}" for s, n in counts.items() if n)
        + f". Sending them to {backend} to extract facts (this can take a while)."
    )
    try:
        extractor, merger = make_providers(backend, allow_api_key=allow_api_key)
        facts = extract_facts(extractor, prompts, progress=lambda m: click.echo(m, err=True))
        records = [r for r in iter_records(home=home) if r.scope == PROFILE_SCOPE]
        edits = propose_edits(merger, records, facts) if facts else []
    except ProviderError as exc:
        raise click.ClickException(str(exc)) from exc
    cost = sum(getattr(p, "cost_usd", 0.0) for p in {id(extractor): extractor, id(merger): merger}.values())
    click.echo(f"{len(facts)} facts found. Model cost estimate: ${cost:.2f}.")

    for source in history.SOURCES:
        newest = max((p.when for p in prompts if p.source == source), default=None)
        if newest is not None and (source not in state or newest > state[source]):
            state[source] = newest
    _write_json(home / STATE_FILE, {s: w.isoformat() for s, w in state.items()})
    if not edits:
        click.echo("No changes to your profile proposed.")
        return None
    proposal = {
        "created": datetime.now(UTC).isoformat(),
        "prompts": counts,
        "facts": facts,
        "cost_usd": round(cost, 4),
        "edits": [asdict(e) for e in edits],
    }
    _write_json(home / PROPOSAL_FILE, proposal)
    return proposal
