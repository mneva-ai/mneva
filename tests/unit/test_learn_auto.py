"""Tests for learn_auto.py: the daily background learn run and its notice.

Popen and the model are faked; nothing is launched and no call leaves the machine.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from mneva import learn as learn_mod
from mneva import learn_auto
from mneva.mcp_server import replay_context
from mneva.store import Record, write_record

NOW = datetime(2026, 5, 10, 9, tzinfo=UTC)


class FakeProvider:
    name = "fake"
    cost_usd = 0.0

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        self.calls += 1
        if learn_mod.PROFILE_MARKER in prompt:
            edit = {"op": "update", "id": "aaaa000000000001", "body": "## 我在做的事\n\n- 新项目", "reason": "新项目"}
            return json.dumps({"edits": [edit]}, ensure_ascii=False)
        return json.dumps({"facts": ["2026-05-03: 开始了新项目"]}, ensure_ascii=False)


@pytest.fixture
def home(tmp_mneva_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv(learn_auto.OFF_VAR, raising=False)
    monkeypatch.setattr(learn_auto.shutil, "which", lambda name: "/bin/claude")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "no-codex"))
    record = Record(id="aaaa000000000001", scope="profile", lifespan="permanent", tool="cli", body="## 我在做的事\n\n- 旧项目")
    write_record(record, home=tmp_mneva_home)
    return tmp_mneva_home


def _history(tmp_path: Path, count: int) -> None:
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir(exist_ok=True)
    rows = [
        {"display": f"第 {n} 个提问, 帮我继续做新项目", "pastedContents": {},
         "timestamp": int((NOW - timedelta(days=1, minutes=n)).timestamp() * 1000), "project": "x", "sessionId": "s"}
        for n in range(count)
    ]
    (claude_dir / "history.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def test_due_only_when_every_gate_passes(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert learn_auto.should_start(home, NOW)

    monkeypatch.setenv(learn_auto.OFF_VAR, "0")
    assert not learn_auto.should_start(home, NOW)
    monkeypatch.delenv(learn_auto.OFF_VAR)

    monkeypatch.setattr(learn_auto.shutil, "which", lambda name: None)
    assert not learn_auto.should_start(home, NOW)
    monkeypatch.setattr(learn_auto.shutil, "which", lambda name: "/bin/claude")

    (home / learn_mod.PROPOSAL_FILE).write_text("{}", encoding="utf-8")
    assert not learn_auto.should_start(home, NOW)
    (home / learn_mod.PROPOSAL_FILE).unlink()

    learn_auto.record_finish(home, NOW - timedelta(hours=2), "no proposal")
    assert not learn_auto.should_start(home, NOW)
    learn_auto.record_finish(home, NOW - learn_auto.INTERVAL - timedelta(minutes=1), "no proposal")
    assert learn_auto.should_start(home, NOW)


def test_not_due_without_a_profile(tmp_mneva_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh install must not send all its history out before the user has a profile.
    monkeypatch.delenv(learn_auto.OFF_VAR, raising=False)
    monkeypatch.setattr(learn_auto.shutil, "which", lambda name: "/bin/claude")
    write_record(Record(id="bbbb000000000001", scope="project", lifespan="permanent", tool="cli", body="x"), home=tmp_mneva_home)
    assert not learn_auto.should_start(tmp_mneva_home, NOW)


def test_a_running_lock_blocks_and_a_stale_one_does_not(home: Path) -> None:
    lock = home / learn_auto.LOCK_FILE
    lock.touch()
    assert not learn_auto.should_start(home, datetime.now(UTC))
    old = time.time() - learn_auto.LOCK_STALE.total_seconds() - 60
    os.utime(lock, (old, old))
    assert learn_auto.should_start(home, datetime.now(UTC))


def test_maybe_start_launches_one_detached_run(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launched: list[dict[str, Any]] = []
    monkeypatch.setattr(learn_auto.subprocess, "Popen", lambda argv, **kw: launched.append({"argv": argv, **kw}))
    learn_auto.maybe_start(home)
    (call,) = launched
    assert call["argv"][-2:] == ["-m", "mneva.learn_auto"]
    # The MCP protocol runs on the server's stdin and stdout; the child must not touch them.
    assert call["stdin"] == subprocess.DEVNULL
    assert str(call["stdout"].name) == str(home / learn_auto.LOG_FILE)
    assert call["env"][learn_auto.OFF_VAR] == "0"


def test_maybe_start_never_raises(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: Any, **kwargs: Any) -> None:
        raise OSError("no")

    monkeypatch.setattr(learn_auto.subprocess, "Popen", boom)
    learn_auto.maybe_start(home)


def test_run_proposes_on_the_login_only(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _history(tmp_path, learn_auto.MIN_PROMPTS)
    fake = FakeProvider()
    seen: dict[str, Any] = {}

    def providers(backend: str, *, allow_api_key: bool = True) -> tuple[FakeProvider, FakeProvider]:
        seen["allow_api_key"] = allow_api_key
        return fake, fake

    monkeypatch.setattr(learn_mod, "make_providers", providers)
    learn_auto.run(home)
    assert seen["allow_api_key"] is False
    assert json.loads((home / learn_mod.PROPOSAL_FILE).read_text(encoding="utf-8"))["edits"]
    assert not (home / learn_auto.LOCK_FILE).exists()
    assert not learn_auto.should_start(home, datetime.now(UTC))


def test_run_with_too_few_prompts_waits_for_more(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _history(tmp_path, learn_auto.MIN_PROMPTS - 1)
    fake = FakeProvider()
    monkeypatch.setattr(learn_mod, "make_providers", lambda backend, **kw: (fake, fake))
    learn_auto.run(home)
    assert fake.calls == 0
    assert not (home / learn_mod.STATE_FILE).exists()  # watermark not moved: these prompts count next time
    assert not learn_auto.should_start(home, datetime.now(UTC))  # but no retry until tomorrow


def test_run_keeps_only_the_newest_prompts(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _history(tmp_path, 50)
    fake = FakeProvider()
    sent: list[str] = []
    monkeypatch.setattr(learn_mod, "make_providers", lambda backend, **kw: (fake, fake))
    monkeypatch.setattr(learn_mod, "extract_facts", lambda provider, prompts, **kw: sent.extend(p.text for p in prompts) or ["2026-05-03: x"])
    monkeypatch.setattr(learn_auto, "MAX_CHARS", 20 * len("第 10 个提问, 帮我继续做新项目"))
    learn_auto.run(home)
    assert len(sent) == 20 and "第 0 个提问" in sent[-1]  # newest last


def test_replay_profile_carries_the_pending_notice(home: Path) -> None:
    assert "mneva learn" not in replay_context(scope="profile")
    proposal = {"edits": [{"op": "update", "id": "aaaa000000000001", "body": "x", "reason": "r"}]}
    (home / learn_mod.PROPOSAL_FILE).write_text(json.dumps(proposal), encoding="utf-8")
    out = replay_context(scope="profile")
    assert "1 proposed change" in out and "mneva learn --accept" in out
    assert "mneva learn" not in replay_context(scope="project")
