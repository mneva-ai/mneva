"""Synthesize 2-stage workflow + digest-to-bootstrap.

All LLM calls go through the Provider Protocol; this module is provider-agnostic.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from mneva.providers import Provider
from mneva.store import iter_records

STAGE1_PROMPT = (
    "You are a creative brainstorming partner. Below is a collection of context "
    "records the user has captured. Read everything, then list 100 distinct ideas, "
    "observations, patterns, connections, or questions that emerge from the material. "
    "Number them 1-100. Be specific and concrete; avoid generic platitudes. "
    "Focus on non-obvious insights and surprising connections.\n\n"
    "=== CAPTURED CONTEXT ===\n"
)

STAGE2_PROMPT = (
    "Below is a shortlist the user selected from a brainstorm. Apply rigorous "
    "critical analysis: for each item, identify the strongest counter-argument, "
    "the most dangerous failure mode, and the one assumption that, if wrong, would "
    "invalidate it. Be specific. Avoid hedging.\n\n"
    "=== SHORTLIST ===\n"
)

DIGEST_PROMPT = (
    "Below are context records the user has captured for the scope {scope!r}. "
    "Distill them into a concise structured summary suitable for inclusion in an "
    "L1 bootstrap file (the document a fresh AI agent reads to get oriented). "
    "Aim for 200-500 words. Preserve concrete facts, decisions, names, and "
    "constraints. Drop redundancy and meta-commentary.\n\n"
    "=== CAPTURED CONTEXT ===\n"
)


def dump_records(*, scope: str, home: Path) -> str:
    """Concatenate all in-scope record bodies with delimiters."""
    blocks: list[str] = []
    for r in iter_records(home=home):
        if r.scope != scope:
            continue
        blocks.append(f"--- record {r.id} (tool={r.tool}, lifespan={r.lifespan}) ---\n{r.body}")
    return "\n\n".join(blocks)


def stage1(provider: Provider, dumped: str, *, max_tokens: int = 8000) -> str:
    """Stage 1: produce ~100 ideas from the full in-scope dump."""
    return provider.complete(STAGE1_PROMPT + dumped, max_tokens=max_tokens)


def stage2(provider: Provider, shortlist: str, *, max_tokens: int = 8000) -> str:
    """Stage 2: critical pass over the user-selected shortlist."""
    return provider.complete(STAGE2_PROMPT + shortlist, max_tokens=max_tokens)


def synthesize_2stage(
    provider: Provider,
    *,
    scope: str,
    home: Path,
    shortlist_input: Callable[[str], str],
    output: Callable[[str], None],
) -> None:
    """Run dump → stage1 → user-cut → stage2.

    `shortlist_input` is called with stage1 output and returns the shortlist text.
    `output` is called twice: once with stage1 output, once with stage2 output.
    Injecting both makes the orchestrator testable without click.
    """
    dumped = dump_records(scope=scope, home=home)
    if not dumped.strip():
        raise ValueError(f"no records found in scope {scope!r}")
    s1 = stage1(provider, dumped)
    output(s1)
    shortlist = shortlist_input(s1)
    s2 = stage2(provider, shortlist)
    output(s2)
