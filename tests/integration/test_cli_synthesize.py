from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from mneva.cli import app
from mneva.store import Record, write_record


@pytest.fixture
def fake_provider_module(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace get_provider with one returning a FakeProvider; record stage outputs."""
    responses = ["STAGE1_OUTPUT", "STAGE2_OUTPUT"]

    class FakeProvider:
        name = "fake"

        def complete(self, prompt: str, *, max_tokens: int) -> str:
            return responses.pop(0)

    def fake_get_provider(name: str) -> FakeProvider:
        return FakeProvider()

    monkeypatch.setattr("mneva.cli.get_provider", fake_get_provider)
    return responses


def test_synthesize_happy_path(
    tmp_mneva_home: Path, fake_provider_module: list[str]
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    write_record(
        Record(
            id="seed", scope="research", lifespan="permanent",
            tool="claude", body="some body",
        ),
        home=tmp_mneva_home,
    )

    result = runner.invoke(
        app,
        ["synthesize", "--scope", "research", "--backend", "anthropic"],
        input="1. keep one\n2. keep two\n.\n",
    )

    assert result.exit_code == 0, result.output
    assert "STAGE1_OUTPUT" in result.output
    assert "STAGE2_OUTPUT" in result.output


def test_synthesize_unknown_scope_errors(
    tmp_mneva_home: Path, fake_provider_module: list[str]
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["synthesize", "--scope", "nope"])
    assert result.exit_code != 0
    assert "no records" in result.output.lower()
