from __future__ import annotations

import json
from pathlib import Path

import pytest

from mneva.distill import (
    DistillResult,
    _parse_response,
    chunk_text,
    distill,
    estimate_cost_usd,
    parse_transcript,
)
from mneva.paths import ensure_home
from mneva.providers.base import ProviderError
from mneva.store import iter_records

# --- parse_transcript ---


def test_parse_transcript_reads_markdown(tmp_path: Path) -> None:
    src = tmp_path / "t.md"
    src.write_text("# header\n\ndecision: ship sqlite", encoding="utf-8")
    assert parse_transcript(src) == "# header\n\ndecision: ship sqlite"


def test_parse_transcript_reads_txt(tmp_path: Path) -> None:
    src = tmp_path / "t.txt"
    src.write_text("plain line", encoding="utf-8")
    assert parse_transcript(src) == "plain line"


def test_parse_transcript_reads_claude_code_session_json(tmp_path: Path) -> None:
    src = tmp_path / "session.json"
    payload = {
        "messages": [
            {"role": "user", "content": "use sqlite?"},
            {"role": "assistant", "content": "yes, zero-ops"},
        ]
    }
    src.write_text(json.dumps(payload), encoding="utf-8")
    out = parse_transcript(src)
    assert "[user] use sqlite?" in out
    assert "[assistant] yes, zero-ops" in out


def test_parse_transcript_falls_back_to_json_dumps_for_unknown_shape(
    tmp_path: Path,
) -> None:
    src = tmp_path / "weird.json"
    payload = {"conversations": [{"id": 1, "title": "foo"}]}
    src.write_text(json.dumps(payload), encoding="utf-8")
    out = parse_transcript(src)
    parsed = json.loads(out)
    assert parsed == payload


def test_parse_transcript_rejects_unsupported_extension(tmp_path: Path) -> None:
    src = tmp_path / "log.zip"
    src.write_bytes(b"\x00")
    with pytest.raises(ValueError) as exc:
        parse_transcript(src)
    assert "unsupported transcript extension" in str(exc.value)


# --- chunk_text ---


def test_chunk_text_returns_single_chunk_for_short_input() -> None:
    assert chunk_text("hello world") == ["hello world"]


def test_chunk_text_splits_long_input_on_paragraph_boundaries() -> None:
    p1 = "a" * 60_000
    p2 = "b" * 60_000
    text = f"{p1}\n\n{p2}"
    chunks = chunk_text(text, max_chars=80_000)
    assert len(chunks) == 2
    assert chunks[0] == p1
    assert chunks[1] == p2


def test_chunk_text_hard_cuts_single_overlong_paragraph() -> None:
    paragraph = "x" * 200_000
    chunks = chunk_text(paragraph, max_chars=80_000)
    assert len(chunks) == 3
    assert all(len(c) <= 80_000 for c in chunks)
    assert "".join(chunks) == paragraph


# --- _parse_response ---


def test_parse_response_extracts_records_from_plain_json() -> None:
    raw = json.dumps(
        {"records": [{"body": "decision: X", "tool": "claude-code", "source": "msg1"}]}
    )
    recs = _parse_response(raw, scope="my-scope", source="src")
    assert len(recs) == 1
    assert recs[0].body == "decision: X"
    assert recs[0].scope == "my-scope"
    assert recs[0].tool == "claude-code"
    assert recs[0].source == "msg1"
    assert recs[0].lifespan == "permanent"


def test_parse_response_tolerates_json_fences() -> None:
    raw = '```json\n{"records":[{"body":"decision: Y"}]}\n```'
    recs = _parse_response(raw, scope="s", source="src")
    assert len(recs) == 1
    assert recs[0].body == "decision: Y"
    assert recs[0].tool == "distill"  # default when LLM omits "tool"


def test_parse_response_raises_provider_error_on_malformed_json() -> None:
    with pytest.raises(ProviderError) as exc:
        _parse_response("not really json {", scope="s", source="src")
    assert "malformed JSON" in str(exc.value)


def test_parse_response_handles_empty_records_list() -> None:
    raw = json.dumps({"records": []})
    assert _parse_response(raw, scope="s", source="src") == []


# --- distill orchestrator ---


class _StubProvider:
    name = "stub"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        self.calls.append(prompt)
        return self._responses.pop(0)


def test_distill_end_to_end_with_mocked_provider(tmp_mneva_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "t.md"
    src.write_text("decision: use sqlite\ndecision: append-mode default", encoding="utf-8")
    home = ensure_home()
    provider = _StubProvider(
        [json.dumps({"records": [
            {"body": "decision: use sqlite for v0", "tool": "claude-code"},
            {"body": "decision: append-mode by default", "tool": "claude-code"},
            {"body": "decision: use sqlite for v0", "tool": "claude-code"},  # dup
        ]})]
    )
    result = distill(provider, source=src, scope="proj", home=home)
    assert isinstance(result, DistillResult)
    assert len(result.written) == 2
    assert result.skipped_dups == 1
    assert result.chunks_processed == 1
    bodies = {r.body for r in iter_records(home=home)}
    assert "decision: use sqlite for v0" in bodies
    assert "decision: append-mode by default" in bodies


def test_distill_refuses_empty_transcript(tmp_mneva_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "empty.md"
    src.write_text("   \n", encoding="utf-8")
    home = ensure_home()
    provider = _StubProvider([])
    with pytest.raises(ValueError) as exc:
        distill(provider, source=src, scope="proj", home=home)
    assert "empty" in str(exc.value)


# --- estimate_cost_usd ---


def test_estimate_cost_anthropic_is_above_threshold_for_real_world_chunk() -> None:
    text = "x" * 80_000
    cost = estimate_cost_usd(text, backend="anthropic", chunks=1)
    assert cost is not None
    assert cost > 0.10  # Opus pricing makes this expensive enough to gate


def test_estimate_cost_returns_none_for_openrouter() -> None:
    assert estimate_cost_usd("anything", backend="openrouter", chunks=1) is None
