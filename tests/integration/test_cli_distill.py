"""CLI-level integration tests for `mneva distill`.

Provider calls are mocked at the `mneva.providers.get_provider` boundary;
this keeps the tests offline and fast.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mneva.cli import app


class _StubProvider:
    name = "stub"

    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        return self._response


@pytest.fixture
def stub_provider(monkeypatch: pytest.MonkeyPatch) -> _StubProvider:
    response = json.dumps(
        {
            "records": [
                {"body": "decision: use sqlite for v0", "tool": "claude-code"},
                {"body": "decision: append-mode by default", "tool": "claude-code"},
            ]
        }
    )
    stub = _StubProvider(response)
    monkeypatch.setattr("mneva.cli.get_provider", lambda _name: stub)
    return stub


def test_distill_happy_path_writes_records_and_summarizes(
    tmp_mneva_home: Path, tmp_path: Path, stub_provider: _StubProvider
) -> None:
    """Default backend is Anthropic Opus, whose 4000-token output budget
    already triggers the >$0.10 gate even on tiny inputs. Pass --yes so
    this test exercises the post-confirm path, not the gate path."""
    runner = CliRunner()
    runner.invoke(app, ["init"])
    src = tmp_path / "session.md"
    src.write_text("we decided to use sqlite and append-mode\n", encoding="utf-8")

    result = runner.invoke(
        app, ["distill", "--source", str(src), "--scope", "proj", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert "distilled 2 records" in result.output
    assert "0 dups skipped" in result.output
    assert "1 chunk(s)" in result.output

    store_files = list((tmp_mneva_home / "store").glob("*.md"))
    assert len(store_files) == 2


def test_distill_refuses_empty_transcript(
    tmp_mneva_home: Path, tmp_path: Path, stub_provider: _StubProvider
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    src = tmp_path / "empty.md"
    src.write_text("   \n", encoding="utf-8")
    # Empty-check happens before the cost gate, so --yes not needed.
    result = runner.invoke(
        app, ["distill", "--source", str(src), "--scope", "proj", "--yes"]
    )
    assert result.exit_code != 0
    assert "empty" in result.output
    assert "Traceback" not in result.output


def test_distill_cost_gate_triggers_above_threshold(
    tmp_mneva_home: Path, tmp_path: Path, stub_provider: _StubProvider
) -> None:
    """Large transcript on Anthropic should trigger the cost-gate prompt."""
    runner = CliRunner()
    runner.invoke(app, ["init"])
    # 80k chars on Anthropic Opus > $0.10 estimated.
    src = tmp_path / "big.md"
    src.write_text("x" * 80_000, encoding="utf-8")
    # Decline the prompt (input "n\n") -> click.confirm aborts.
    result = runner.invoke(
        app,
        ["distill", "--source", str(src), "--scope", "proj", "--backend", "anthropic"],
        input="n\n",
    )
    assert result.exit_code != 0
    assert "costing approximately" in result.output


def test_distill_yes_flag_bypasses_cost_gate(
    tmp_mneva_home: Path, tmp_path: Path, stub_provider: _StubProvider
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    src = tmp_path / "big.md"
    src.write_text("x" * 80_000, encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "distill",
            "--source",
            str(src),
            "--scope",
            "proj",
            "--backend",
            "anthropic",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "distilled 2 records" in result.output
