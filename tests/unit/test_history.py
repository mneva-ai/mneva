"""Tests for history.py: reading the user's own prompts from local tool history.

Fixtures copy the record shapes measured on real installs on 2026-10-18
(see .claude/specs/p1-history-import.spec.md); the texts are made up.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mneva.history import CLAUDE_CODE, CODEX, MAX_CHARS, collect


@pytest.fixture(autouse=True)
def _no_tool_home_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    # Both variables win over the home directory; a developer's own would
    # otherwise leak real history into these tests.
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)


def _ms(day: int) -> int:
    return int(datetime(2026, 5, day, 12, tzinfo=UTC).timestamp() * 1000)


def _iso(day: int) -> str:
    return datetime(2026, 5, day, 12, tzinfo=UTC).isoformat().replace("+00:00", "Z")


def _write_claude(home: Path, rows: list[dict]) -> None:
    path = home / ".claude" / "history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.write("not json\n")


def _claude_row(day: int, text: str, pasted: dict | None = None) -> dict:
    return {
        "display": text,
        "pastedContents": pasted or {},
        "timestamp": _ms(day),
        "project": "D:\\work\\app",
        "sessionId": "s1",
    }


def _codex_user(day: int, *texts: str) -> dict:
    return {
        "timestamp": _iso(day),
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": t} for t in texts],
        },
    }


def _write_codex(home: Path, name: str, lines: list[dict]) -> None:
    path = home / ".codex" / "sessions" / "2026" / "05" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines), encoding="utf-8")


def test_claude_code_keeps_typed_prompts_only(tmp_path: Path) -> None:
    _write_claude(
        tmp_path,
        [
            _claude_row(1, "/clear"),
            _claude_row(2, "<command-name>/plan</command-name>"),
            _claude_row(3, "<task-notification>\n<task-id>x</task-id>"),
            _claude_row(4, "[Request interrupted by user]"),
            _claude_row(5, "ok"),
            _claude_row(6, "我在做一个 花园日记 App [Pasted text #1 +40 lines]", {"1": {"content": "SECRET DOC"}}),
        ],
    )
    prompts = collect({}, user_home=tmp_path)
    assert [(p.source, p.text) for p in prompts] == [(CLAUDE_CODE, "我在做一个 花园日记 App")]


def test_codex_drops_injected_turns_and_keeps_the_request(tmp_path: Path) -> None:
    _write_codex(
        tmp_path,
        "a.jsonl",
        [
            {"timestamp": _iso(1), "type": "session_meta", "payload": {"cwd": "D:\\work"}},
            _codex_user(1, "# AGENTS.md instructions for D:\\work\n\nbe nice"),
            _codex_user(1, "<environment_context>\n  <cwd>D:\\work</cwd>"),
            _codex_user(2, "# Context from my IDE setup:\n\n## Open tabs:\n- a.py\n\n## My request for Codex:\n帮我把读书笔记网站部署到 Railway"),
            _codex_user(3, "<image name=[Image #1]>\n\n</image>", "截图里的报错怎么修"),
            {"timestamp": _iso(4), "type": "response_item",
             "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "AI text here"}]}},
            {"timestamp": _iso(4), "type": "response_item",
             "payload": {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "developer text"}]}},
        ],
    )
    prompts = collect({}, user_home=tmp_path)
    assert [(p.source, p.text) for p in prompts] == [
        (CODEX, "帮我把读书笔记网站部署到 Railway"),
        (CODEX, "截图里的报错怎么修"),
    ]


def test_secrets_are_redacted_and_long_text_is_capped(tmp_path: Path) -> None:
    key = "sk-ant-" + "a" * 40
    _write_claude(tmp_path, [_claude_row(1, f"用这个 key {key} 调接口"), _claude_row(2, "长" * 5000)])
    first, second = collect({}, user_home=tmp_path)
    assert key not in first.text and "[redacted]" in first.text
    assert len(second.text) <= MAX_CHARS + 20


def test_collect_is_time_ordered_deduplicated_and_respects_watermarks(tmp_path: Path) -> None:
    _write_claude(tmp_path, [_claude_row(1, "旧的提问不要了"), _claude_row(5, "我想要更便宜的模型"), _claude_row(7, "继续执行这个计划")])
    _write_codex(tmp_path, "b.jsonl", [_codex_user(3, "我想要更便宜的模型"), _codex_user(6, "记得用中文回答我")])
    watermark = {CLAUDE_CODE: datetime(2026, 5, 2, tzinfo=UTC)}
    prompts = collect(watermark, user_home=tmp_path)
    # Day 1 is behind the watermark; the day-5 repeat of a day-3 prompt is dropped.
    assert [(p.source, p.text) for p in prompts] == [
        (CODEX, "我想要更便宜的模型"),
        (CODEX, "记得用中文回答我"),
        (CLAUDE_CODE, "继续执行这个计划"),
    ]


def test_missing_history_is_empty(tmp_path: Path) -> None:
    assert collect({}, user_home=tmp_path) == []
