from __future__ import annotations

from pathlib import Path

from mneva.replay import render_replay
from mneva.store import Record, write_record


def test_replay_template_claude_code(tmp_mneva_home: Path) -> None:
    record = Record(
        id="t751-claude-code",
        scope="t751",
        lifespan="permanent",
        tool="claude-code",
        body="UNIQUE-BODY-MARKER-claude-code",
    )
    write_record(record, home=tmp_mneva_home)

    output = render_replay(tool="claude-code", scope="t751", home=tmp_mneva_home)

    assert isinstance(output, str)
    assert "--tool=claude-code" in output
    assert "UNIQUE-BODY-MARKER-claude-code" in output
    assert "t751-claude-code" in output


def test_replay_template_cursor(tmp_mneva_home: Path) -> None:
    record = Record(
        id="t751-cursor",
        scope="t751",
        lifespan="permanent",
        tool="cursor",
        body="UNIQUE-BODY-MARKER-cursor",
    )
    write_record(record, home=tmp_mneva_home)

    output = render_replay(tool="cursor", scope="t751", home=tmp_mneva_home)

    assert isinstance(output, str)
    assert "--tool=cursor" in output
    assert "UNIQUE-BODY-MARKER-cursor" in output
    assert "t751-cursor" in output
    assert "alwaysApply" not in output


def test_replay_template_codex(tmp_mneva_home: Path) -> None:
    record = Record(
        id="t751-codex",
        scope="t751",
        lifespan="permanent",
        tool="codex",
        body="UNIQUE-BODY-MARKER-codex",
    )
    write_record(record, home=tmp_mneva_home)

    output = render_replay(tool="codex", scope="t751", home=tmp_mneva_home)

    assert isinstance(output, str)
    assert "--tool=codex" in output
    assert "UNIQUE-BODY-MARKER-codex" in output
    assert "t751-codex" in output
