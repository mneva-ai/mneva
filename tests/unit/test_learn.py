"""Tests for ``mneva learn``: profile edits proposed from history, applied only on accept.

A fake provider stands in for the model, so no call leaves the machine. The
real-data check is the founder's own run (see the spec's release gate).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from mneva import learn as learn_mod
from mneva.cli import app
from mneva.learn import Edit, propose_edits
from mneva.store import Record, iter_records, read_record, write_record

EXTRACT_REPLY = json.dumps({"facts": ["2026-05-03: 在做 花园日记 App的前端重构"]}, ensure_ascii=False)


class FakeProvider:
    name = "fake"

    def __init__(self, merge_reply: str) -> None:
        self.merge_reply = merge_reply
        self.calls: list[str] = []
        self.cost_usd = 0.01

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        self.calls.append(prompt)
        return self.merge_reply if learn_mod.PROFILE_MARKER in prompt else EXTRACT_REPLY


def _record(rid: str, body: str, scope: str = "profile") -> Record:
    return Record(id=rid, scope=scope, lifespan="permanent", tool="cli", body=body)


@pytest.fixture
def setup(tmp_mneva_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    ms = int(datetime(2026, 5, 3, tzinfo=UTC).timestamp() * 1000)
    row = {"display": "帮我重构 花园日记 App的前端", "pastedContents": {}, "timestamp": ms, "project": "x", "sessionId": "s"}
    (claude_dir / "history.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_dir))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "no-codex"))

    for rec in (
        _record("aaaa000000000001", "## 我在做的事\n\n- 花园日记 App: 数据同步"),
        _record("aaaa000000000002", "## 当前优先级\n\n- 旧的优先级"),
        _record("bbbb000000000003", "a repo memory", scope="project"),
    ):
        write_record(rec, home=tmp_mneva_home)

    merge_reply = json.dumps(
        {
            "edits": [
                {"op": "update", "id": "aaaa000000000001", "body": "## 我在做的事\n\n- 花园日记 App: 前端重构", "reason": "5 月开始重构前端"},
                {"op": "add", "body": "## 偏好\n\n- 用中文回答", "reason": "多次要求中文"},
                {"op": "remove", "id": "aaaa000000000002", "reason": "已过时"},
            ]
        },
        ensure_ascii=False,
    )
    fake = FakeProvider(merge_reply)
    monkeypatch.setattr(learn_mod, "make_providers", lambda backend, **kw: (fake, fake))
    return tmp_mneva_home, fake


def test_learn_proposes_then_applies_only_accepted_edits(setup) -> None:
    home, fake = setup
    runner = CliRunner()

    result = runner.invoke(app, ["learn"])
    assert result.exit_code == 0, result.output
    assert "1." in result.output and "前端重构" in result.output and "--accept" in result.output
    assert len(fake.calls) == 2  # one extract chunk, one merge
    # Nothing written yet.
    assert read_record("aaaa000000000001", home=home).body.endswith("数据同步")
    assert len(list(iter_records(home=home))) == 3

    result = runner.invoke(app, ["learn", "--accept", "1,3"])
    assert result.exit_code == 0, result.output
    updated = read_record("aaaa000000000001", home=home)
    assert updated.body.endswith("前端重构") and updated.scope == "profile" and updated.tool == "cli"
    ids = {r.id for r in iter_records(home=home)}
    assert ids == {"aaaa000000000001", "bbbb000000000003"}  # 2 removed, add (#2) skipped
    assert not (home / learn_mod.PROPOSAL_FILE).exists()


def test_second_run_without_new_prompts_makes_no_call(setup) -> None:
    home, fake = setup
    runner = CliRunner()
    runner.invoke(app, ["learn"])
    runner.invoke(app, ["learn", "--discard"])
    calls = len(fake.calls)

    result = runner.invoke(app, ["learn"])
    assert result.exit_code == 0, result.output
    assert "Nothing new" in result.output
    assert len(fake.calls) == calls
    assert not (home / learn_mod.PROPOSAL_FILE).exists()


def test_pending_proposal_is_shown_before_new_extraction(setup) -> None:
    _, fake = setup
    runner = CliRunner()
    runner.invoke(app, ["learn"])
    calls = len(fake.calls)

    result = runner.invoke(app, ["learn"])
    assert result.exit_code == 0, result.output
    assert "前端重构" in result.output
    assert len(fake.calls) == calls


def test_accept_all_adds_a_profile_record(setup) -> None:
    home, _ = setup
    runner = CliRunner()
    runner.invoke(app, ["learn"])
    result = runner.invoke(app, ["learn", "--accept", "all"])
    assert result.exit_code == 0, result.output
    added = [r for r in iter_records(home=home) if "用中文回答" in r.body]
    assert len(added) == 1 and added[0].scope == "profile" and added[0].lifespan == "permanent"


def test_invalid_edits_are_dropped() -> None:
    records = [_record("aaaa000000000001", "## 我是谁\n\n- Nick")]
    reply = json.dumps(
        {
            "edits": [
                {"op": "update", "id": "ffff000000000000", "body": "x", "reason": "unknown id"},
                {"op": "update", "id": "aaaa000000000001", "body": "## 我是谁\n\n- Nick", "reason": "unchanged"},
                {"op": "rewrite", "id": "aaaa000000000001", "body": "x", "reason": "bad op"},
                {"op": "add", "body": "  ", "reason": "empty"},
                {"op": "remove", "id": "aaaa000000000001", "reason": "ok"},
            ]
        }
    )
    edits = propose_edits(FakeProvider(reply), records, ["fact"])
    assert edits == [Edit(op="remove", id="aaaa000000000001", body=None, reason="ok")]
