from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from mneva import brief
from mneva.cli import app
from mneva.store import Record, write_record


def _profile(home: Path, rid: str, body: str) -> None:
    write_record(
        Record(id=rid, scope="profile", lifespan="permanent", tool="cli", body=body),
        home=home,
    )


def test_brief_prints_profile(tmp_mneva_home: Path) -> None:
    _profile(tmp_mneva_home, "p1", "I make short product videos.")

    result = CliRunner().invoke(app, ["brief"])

    assert result.exit_code == 0, result.output
    assert "I make short product videos." in result.output


def test_brief_without_profile_explains_how_to_add_one(tmp_mneva_home: Path) -> None:
    result = CliRunner().invoke(app, ["brief"])

    assert result.exit_code != 0
    assert "--scope profile" in result.output


def test_brief_reports_skipped_records(tmp_mneva_home: Path) -> None:
    _profile(tmp_mneva_home, "p1", "short")
    _profile(tmp_mneva_home, "p2", "y" * 500)

    result = CliRunner().invoke(app, ["brief", "--max-chars", "200"])

    assert result.exit_code == 0, result.output
    assert "p2" in result.output  # named in the skipped warning
    assert "y" * 10 not in result.output


def test_brief_copy_puts_text_on_clipboard_not_stdout(
    tmp_mneva_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _profile(tmp_mneva_home, "p1", "BODY-FOR-CLIPBOARD")
    copied: list[str] = []
    monkeypatch.setattr(brief, "copy_to_clipboard", copied.append)

    result = CliRunner().invoke(app, ["brief", "--copy"])

    assert result.exit_code == 0, result.output
    assert len(copied) == 1 and "BODY-FOR-CLIPBOARD" in copied[0]
    assert "BODY-FOR-CLIPBOARD" not in result.output
    assert "copied" in result.output.lower()
