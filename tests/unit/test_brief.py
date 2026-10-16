from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from mneva import brief
from mneva.brief import (
    PROFILE_SCOPE,
    ClipboardError,
    copy_to_clipboard,
    record_copy,
    render_brief,
    stale_copies,
)
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


def _copy(home: Path, max_chars: int) -> None:
    text = render_brief(home=home, max_chars=max_chars).text
    record_copy(text=text, max_chars=max_chars, scope=PROFILE_SCOPE, home=home)


def test_copied_brief_goes_stale_when_the_profile_changes(tmp_mneva_home: Path) -> None:
    _write(tmp_mneva_home, "e1", "first")
    _copy(tmp_mneva_home, 4000)
    assert stale_copies(home=tmp_mneva_home) == []

    _write(tmp_mneva_home, "e2", "second")

    assert stale_copies(home=tmp_mneva_home) == [(PROFILE_SCOPE, 4000)]


def test_each_budget_is_tracked_without_naming_the_tool(tmp_mneva_home: Path) -> None:
    # A 1500-char copy (ChatGPT) and a full copy (anything else) are two
    # different pastes; both must be remembered with no extra input.
    _write(tmp_mneva_home, "h1", "first")
    _copy(tmp_mneva_home, 1500)
    _copy(tmp_mneva_home, 4000)

    _write(tmp_mneva_home, "h2", "second")

    assert stale_copies(home=tmp_mneva_home) == [(PROFILE_SCOPE, 1500), (PROFILE_SCOPE, 4000)]


def test_change_that_never_fit_the_budget_is_not_stale(tmp_mneva_home: Path) -> None:
    # The pasted text is what matters: a record skipped for that budget
    # never reached the tool, so changing it changes nothing there.
    _write(tmp_mneva_home, "f1", "short")
    _copy(tmp_mneva_home, 200)

    _write(tmp_mneva_home, "f2", "x" * 500)

    assert stale_copies(home=tmp_mneva_home) == []


def test_change_in_another_scope_is_not_stale(tmp_mneva_home: Path) -> None:
    _write(tmp_mneva_home, "g1", "me")
    _copy(tmp_mneva_home, 4000)

    _write(tmp_mneva_home, "g2", "work note", scope="work")

    assert stale_copies(home=tmp_mneva_home) == []


def test_unreadable_copy_log_counts_as_no_copies(tmp_mneva_home: Path) -> None:
    # A reminder must never break a capture.
    (tmp_mneva_home / brief.COPIES_FILE).write_text("{not json", encoding="utf-8")

    assert stale_copies(home=tmp_mneva_home) == []


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
