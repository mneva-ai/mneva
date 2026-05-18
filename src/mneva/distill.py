"""Distill: extract permanent context records from raw conversation logs.

Pipeline:
  1. ``parse_transcript`` — read .md / .txt / .json (Claude Code session
     shape ``{messages: [{role, content}]}`` is recognised; other JSON
     shapes pass through as ``json.dumps``).
  2. ``chunk_text`` — split if longer than ``_CHUNK_CHARS`` (default 80k,
     safe for 200k-context models with 4k response budget). Splits on
     paragraph boundaries first, hard-cuts on the upper bound.
  3. ``_call_llm_for_chunk`` — call ``provider.complete`` with the
     extraction prompt + the chunk; parse the response JSON.
  4. ``distill`` orchestrator — loop chunks, dedup by content-hash,
     write each new record via ``store.write_record`` + ``Indexer.add``,
     return ``DistillResult``.

The module stays provider-agnostic and free of CLI concerns: vault mirror
and cost-gate confirmation happen in ``cli.distill``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from mneva.indexer import Indexer
from mneva.providers import Provider, ProviderError
from mneva.store import Record, make_record_id, write_record

_CHUNK_CHARS = 80_000  # Safe for 200k-context Anthropic with 4k response budget
_MAX_OUTPUT_TOKENS = 4000
_SUPPORTED_EXTENSIONS = frozenset({".md", ".txt", ".json"})

_DISTILL_PROMPT = """You are extracting permanent context records from a raw
AI conversation transcript. Identify items that meet ALL of these criteria:

  1. A decision was made, a constraint was named, a fact was established,
     or a pattern/convention was set.
  2. The item survives across sessions (not transient debugging like
     "let me try X" or "what does Y look like").
  3. It is not already obvious from the project name alone.

Output STRICTLY valid JSON in this exact shape:

{
  "records": [
    {"body": "decision: ...", "tool": "claude-code", "source": "<short hint>"},
    ...
  ]
}

Rules:
  - Cap at 20 records per response.
  - Each "body" should be 1-3 sentences, self-contained, in the user's voice.
  - "tool" is optional; defaults to "distill" if omitted.
  - "source" is optional; one-line hint at where in the transcript it came from.
  - Skip pleasantries, debug output, tool error messages, and partial thoughts.
  - If the transcript has zero qualifying items, return {"records": []}.

=== TRANSCRIPT ===
"""


@dataclass(frozen=True, slots=True)
class DistillResult:
    """Result of one ``distill`` invocation."""

    written: list[Record] = field(default_factory=list)
    skipped_dups: int = 0
    chunks_processed: int = 0


def parse_transcript(path: Path) -> str:
    """Return transcript content as plain text. Format dispatched on extension.

    Supported extensions (case-insensitive): ``.md``, ``.txt``, ``.json``.
    JSON files are checked for the Claude Code session shape
    ``{messages: [{role, content}, ...]}`` and reformatted role-prefixed.
    Other shapes fall back to ``json.dumps`` (the LLM is good at handling
    raw JSON anyway).

    Raises ``ValueError`` on unsupported extensions or unreadable JSON.
    """
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"unsupported transcript extension {suffix!r}; "
            f"supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )

    text = path.read_text(encoding="utf-8")
    if suffix in {".md", ".txt"}:
        return text

    # .json
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"transcript at {path} is not valid JSON: {e.msg} "
            f"(line {e.lineno}, column {e.colno})"
        ) from e

    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        parts: list[str] = []
        for msg in data["messages"]:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            parts.append(f"[{role}] {content}")
        return "\n\n".join(parts)

    # Generic JSON: hand it to the LLM as a pretty dump.
    return json.dumps(data, indent=2, ensure_ascii=False)


def chunk_text(text: str, max_chars: int = _CHUNK_CHARS) -> list[str]:
    """Split text into chunks of <= ``max_chars`` characters.

    Splits on ``\\n\\n`` boundaries when possible to preserve paragraph
    coherence. Falls back to hard-cut when a single paragraph exceeds the
    limit (e.g. a giant single-line JSON dump).
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)

    # Second pass: hard-cut any chunk that's still too big (e.g. a single
    # giant paragraph with no \\n\\n inside).
    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final.append(chunk)
        else:
            for i in range(0, len(chunk), max_chars):
                final.append(chunk[i : i + max_chars])
    return final


def _content_hash(body: str) -> str:
    return hashlib.sha256(body.strip().encode("utf-8")).hexdigest()[:16]


def _strip_json_fences(raw: str) -> str:
    """Tolerate ```json ... ``` fenced responses from chatty models."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        # Drop opening fence + optional `json` language hint.
        first_newline = stripped.find("\n")
        stripped = stripped[first_newline + 1 :] if first_newline >= 0 else stripped[3:]
        if stripped.endswith("```"):
            stripped = stripped[: -3].rstrip()
    return stripped.strip()


def _parse_response(raw: str, *, scope: str, source: str) -> list[Record]:
    """Parse one LLM response into a list of Record candidates.

    Raises ``ProviderError`` on malformed JSON or on response.records that
    is not a list. Empty records list is valid (returns []).
    """
    cleaned = _strip_json_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        snippet = raw[:200].replace("\n", " ")
        raise ProviderError(
            f"distill: LLM returned malformed JSON ({e.msg} line {e.lineno}); "
            f"raw[:200]={snippet!r}"
        ) from e

    if not isinstance(data, dict):
        raise ProviderError(
            f"distill: LLM response must be a JSON object; got {type(data).__name__}"
        )
    records_field = data.get("records")
    if records_field is None:
        return []
    if not isinstance(records_field, list):
        raise ProviderError(
            f"distill: response.records must be a list; got {type(records_field).__name__}"
        )

    out: list[Record] = []
    for item in records_field:
        if not isinstance(item, dict):
            continue
        body = str(item.get("body", "")).strip()
        if not body:
            continue
        out.append(
            Record(
                id=make_record_id(scope, body),
                scope=scope,
                lifespan="permanent",
                tool=str(item.get("tool") or "distill"),
                body=body,
                source=item.get("source") or source,
            )
        )
    return out


def distill(
    provider: Provider,
    *,
    source: Path,
    scope: str,
    home: Path,
    max_records_per_chunk: int = 20,
) -> DistillResult:
    """Extract permanent records from a transcript via the configured LLM.

    Idempotent across runs against the same transcript content: dedup is
    by content-hash within this call; cross-run dedup happens at the
    ``store.write_record`` layer (``FileExistsError`` is caught and counted
    as a skipped dup).
    """
    text = parse_transcript(source)
    if not text.strip():
        raise ValueError(f"distill: transcript {source} is empty")

    chunks = chunk_text(text)
    seen_hashes: set[str] = set()
    written: list[Record] = []
    skipped_dups = 0
    indexer = Indexer(home / "mneva.sqlite")

    for chunk in chunks:
        raw = provider.complete(_DISTILL_PROMPT + chunk, max_tokens=_MAX_OUTPUT_TOKENS)
        candidates = _parse_response(raw, scope=scope, source=source.name)[
            :max_records_per_chunk
        ]
        for rec in candidates:
            content_hash = _content_hash(rec.body)
            if content_hash in seen_hashes:
                skipped_dups += 1
                continue
            seen_hashes.add(content_hash)
            try:
                write_record(rec, home=home, overwrite=False)
            except FileExistsError:
                # Record id collision = identical scope+timestamp+body prefix.
                # Practically impossible inside one distill run; here for safety.
                skipped_dups += 1
                continue
            indexer.add(rec)
            written.append(rec)

    return DistillResult(
        written=written,
        skipped_dups=skipped_dups,
        chunks_processed=len(chunks),
    )


# --- Cost estimation helpers (called from cli.distill) ---

# Prices in USD per 1M tokens, conservative defaults for cost-gate warnings.
# These are estimates, not a billing source of truth.
_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "anthropic": (15.00, 75.00),   # Opus 4.7
    "openai": (2.00, 10.00),       # gpt-5 estimate
    "google": (1.25, 5.00),        # gemini-2.0-pro
    # "openrouter" intentionally absent — varies by model; skip the gate
}


def estimate_cost_usd(text: str, *, backend: str, chunks: int) -> float | None:
    """Return rough cost estimate in USD, or None if pricing unknown.

    Heuristic: ``len(text)/4`` ≈ input tokens; output budget is
    ``_MAX_OUTPUT_TOKENS`` per chunk. Returns ``None`` for backends not in
    ``_PRICE_TABLE`` (e.g. ``openrouter``).
    """
    if backend not in _PRICE_TABLE:
        return None
    input_per_m, output_per_m = _PRICE_TABLE[backend]
    input_tokens = len(text) / 4
    output_tokens = _MAX_OUTPUT_TOKENS * chunks
    return (input_tokens * input_per_m + output_tokens * output_per_m) / 1_000_000
