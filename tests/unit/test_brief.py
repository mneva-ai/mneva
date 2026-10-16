from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from mneva import brief
from mneva.brief import PROFILE_SCOPE, ClipboardError, copy_to_clipboard, render_brief
from mneva.store import Record, write_record


def _write(home: Path, rid: str, body: str, **fields: Any) -> None:
    fields.setdefault("scope", PROFILE_SCOPE)
    fields.setdefault("lifespan", "permanent")
    write_record(Record(id=rid, tool="cli", body=body, **fields), home=home)


def test_brief_includes_only_permanent_profile_records(tmp_mneva_home: Path) -> None:
    _write(tmp_mneva_home, "a1", "PROFILE-KEEP")
    _write(tmp_mneva_home, "a2", "OTHER-SCOPE", scope="work")
    _write(tmp_mneva_home, "a3", "TRANSIENT-PROFILE", lifespan="transient")

    result = render_brief(home=tmp_mneva_home, max_chars=4000)

    assert "PROFILE-KEEP" in result.text
    assert "OTHER-SCOPE" not in result.text
    assert "TRANSIENT-PROFILE" not in result.text
    assert result.included == ["a1"]


def test_brief_ignores_repo_because_profile_is_global(tmp_mneva_home: Path) -> None:
    # A profile captured inside some repo must still travel to every tool.
    _write(tmp_mneva_home, "b1", "FROM-A-REPO", repo="github.com/org/other")

    result = render_brief(home=tmp_mneva_home, max_chars=4000)

    assert "FROM-A-REPO" in result.text


def test_brief_skips_records_that_do_not_fit_and_reports_them(tmp_mneva_home: Path) -> None:
    _write(tmp_mneva_home, "c1", "short")
    _write(tmp_mneva_home, "c2", "x" * 500)
    _write(tmp_mneva_home, "c3", "also short")

    result = render_brief(home=tmp_mneva_home, max_chars=200)

    assert len(result.text) <= 200
    assert result.included == ["c1", "c3"]
    assert result.skipped == ["c2"]
    # Whole records only: never a record cut off mid-sentence.
    assert "x" * 10 not in result.text


def test_brief_with_no_profile_records_is_empty(tmp_mneva_home: Path) -> None:
    result = render_brief(home=tmp_mneva_home, max_chars=4000)

    assert result.included == []
    assert result.text == ""


def test_brief_scope_override(tmp_mneva_home: Path) -> None:
    _write(tmp_mneva_home, "d1", "BRAND-NOTES", scope="brand")

    result = render_brief(home=tmp_mneva_home, max_chars=4000, scope="brand")

    assert "BRAND-NOTES" in result.text


def test_copy_on_windows_uses_win32_api_not_clip(monkeypatch: pytest.MonkeyPatch) -> None:
    # clip.exe guesses encodings: a BOM survives as U+FEFF, and short CJK
    # text without one is misread as ANSI. Windows must bypass it.
    sent: list[str] = []

    def no_subprocess(*_: Any, **__: Any) -> None:
        raise AssertionError("clip.exe must not be used on Windows")

    monkeypatch.setattr(brief.sys, "platform", "win32")
    monkeypatch.setattr(brief, "_copy_windows", sent.append)
    monkeypatch.setattr(brief.subprocess, "run", no_subprocess)

    copy_to_clipboard("你")

    assert sent == ["你"]


def test_copy_missing_tool_raises_clipboard_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(*_: Any, **__: Any) -> None:
        raise FileNotFoundError("xclip")

    monkeypatch.setattr(brief.sys, "platform", "linux")
    monkeypatch.setattr(brief.subprocess, "run", missing)

    with pytest.raises(ClipboardError):
        copy_to_clipboard("x")


def test_copy_nonzero_exit_raises_clipboard_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(cmd: list[str], **_: Any) -> None:
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(brief.sys, "platform", "linux")
    monkeypatch.setattr(brief.subprocess, "run", failing)

    with pytest.raises(ClipboardError):
        copy_to_clipboard("x")
