"""Tests for the `claude -p` provider. subprocess is faked; no model is called."""
from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from mneva.providers import ProviderError, claude_cli


def _reply(text: str, cost: float = 0.02, is_error: bool = False) -> str:
    return json.dumps({"result": text, "is_error": is_error, "total_cost_usd": cost})


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    monkeypatch.setattr(claude_cli.shutil, "which", lambda name: "/bin/claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    return []


def _fake_run(calls: list[dict[str, Any]], replies: list[subprocess.CompletedProcess[str]]):
    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"argv": argv, **kwargs})
        return replies[len(calls) - 1]

    return run


def _done(stdout: str, code: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


def test_runs_isolated_on_the_login_first(calls, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_cli.subprocess, "run", _fake_run(calls, [_done(_reply("好的"))]))
    provider = claude_cli.ClaudeCliProvider(model="sonnet")
    assert provider.complete("提问", max_tokens=100) == "好的"
    (call,) = calls
    argv = call["argv"]
    for flag in ("-p", "--no-session-persistence", "--strict-mcp-config"):
        assert flag in argv
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert call["input"] == "提问" and call["encoding"] == "utf-8"
    assert "ANTHROPIC_API_KEY" not in call["env"]
    assert provider.cost_usd == pytest.approx(0.02)


def test_falls_back_to_the_api_key_when_no_login(calls, monkeypatch: pytest.MonkeyPatch) -> None:
    replies = [_done("Not logged in · Please run /login", code=1), _done(_reply("ok", cost=0.05))]
    monkeypatch.setattr(claude_cli.subprocess, "run", _fake_run(calls, replies))
    provider = claude_cli.ClaudeCliProvider(model="sonnet")
    assert provider.complete("x", max_tokens=100) == "ok"
    assert calls[1]["env"]["ANTHROPIC_API_KEY"] == "sk-test"
    assert provider.cost_usd == pytest.approx(0.05)
    # Later calls go straight to the key.
    monkeypatch.setattr(claude_cli.subprocess, "run", _fake_run(calls, [*replies, _done(_reply("again"))]))
    provider.complete("y", max_tokens=100)
    assert calls[2]["env"]["ANTHROPIC_API_KEY"] == "sk-test"


def test_error_reply_raises(calls, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setattr(claude_cli.subprocess, "run", _fake_run(calls, [_done(_reply("overloaded", is_error=True))]))
    with pytest.raises(ProviderError, match="overloaded"):
        claude_cli.ClaudeCliProvider(model="sonnet").complete("x", max_tokens=100)


def test_missing_claude_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_cli.shutil, "which", lambda name: None)
    with pytest.raises(ProviderError, match="claude"):
        claude_cli.ClaudeCliProvider(model="sonnet")
