"""Tests for ``mneva upgrade`` — install-method detection + the CLI command.

Detection is a pure function over ``sys.prefix``, so every branch is exercised
by injecting a synthetic prefix string. The CLI tests monkeypatch detection and
``subprocess.run`` so no real upgrade ever runs.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from click.testing import CliRunner

from mneva import upgrade as upgrade_mod
from mneva.cli import app
from mneva.upgrade import (
    PIP,
    PIPX,
    UV_TOOL,
    UVX,
    detect_install_method,
    plan_for,
)

# --- detect_install_method ------------------------------------------------


def test_detect_pipx() -> None:
    assert detect_install_method("/home/u/.local/pipx/venvs/mneva") == PIPX


def test_detect_uv_tool() -> None:
    assert detect_install_method("/home/u/.local/share/uv/tools/mneva") == UV_TOOL


@pytest.mark.parametrize(
    "prefix",
    [
        "/home/u/.cache/uv/archive-v0/abcdef",
        "/home/u/.local/share/uv/cache/builds-v0/xyz",
        "C:/Users/u/AppData/Local/uv/cache/archive-v0/q",
    ],
)
def test_detect_uvx_ephemeral(prefix: str) -> None:
    assert detect_install_method(prefix) == UVX


def test_detect_pip_fallback() -> None:
    # A plain venv / system prefix matches none of the markers.
    assert detect_install_method("/usr/local") == PIP
    assert detect_install_method("/home/u/project/.venv") == PIP


def test_detect_windows_backslash_pipx() -> None:
    assert detect_install_method(r"C:\Users\u\pipx\venvs\mneva") == PIPX


def test_detect_windows_backslash_uv_tool() -> None:
    assert detect_install_method(r"C:\Users\u\AppData\Roaming\uv\tools\mneva") == UV_TOOL


def test_detect_default_prefix_returns_known_method() -> None:
    # No argument -> reads sys.prefix; must classify into one of the four.
    assert detect_install_method() in {PIPX, UV_TOOL, UVX, PIP}


# --- plan_for -------------------------------------------------------------


def test_plan_pipx_command() -> None:
    plan = plan_for(PIPX)
    assert plan.command == ["pipx", "upgrade", "mneva"]
    assert "pipx" in plan.message


def test_plan_uv_tool_command() -> None:
    plan = plan_for(UV_TOOL)
    assert plan.command == ["uv", "tool", "upgrade", "mneva"]


def test_plan_uvx_has_no_command() -> None:
    plan = plan_for(UVX)
    assert plan.command is None
    assert "uvx" in plan.message


def test_plan_pip_uses_current_interpreter() -> None:
    plan = plan_for(PIP)
    assert plan.command is not None
    assert plan.command[0] == sys.executable
    assert plan.command[1:] == ["-m", "pip", "install", "--upgrade", "mneva"]


# --- CLI: mneva upgrade ---------------------------------------------------

SETUP = [sys.executable, "-m", "mneva.cli", "setup", "--after-upgrade"]


def _recording_run(
    monkeypatch: pytest.MonkeyPatch, returncodes: dict[str, int] | None = None
) -> list[list[str]]:
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], **_k: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(cmd)
        code = (returncodes or {}).get("setup" if cmd == SETUP else "upgrade", 0)
        return subprocess.CompletedProcess(cmd, returncode=code)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    return calls


def test_upgrade_dry_run_does_not_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upgrade_mod, "detect_install_method", lambda: PIP)

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("subprocess.run must not be called in --dry-run")

    monkeypatch.setattr(subprocess, "run", _boom)
    result = CliRunner().invoke(app, ["upgrade", "--dry-run"])
    assert result.exit_code == 0
    assert "would run:" in result.output
    assert "mneva setup" in result.output


def test_upgrade_then_refreshes_setup_in_a_new_process(monkeypatch: pytest.MonkeyPatch) -> None:
    # A new process, because this one still runs the version being replaced.
    monkeypatch.setattr(upgrade_mod, "detect_install_method", lambda: PIPX)
    calls = _recording_run(monkeypatch)

    result = CliRunner().invoke(app, ["upgrade"])

    assert result.exit_code == 0
    assert calls == [["pipx", "upgrade", "mneva"], SETUP]
    assert "complete" in result.output


def test_upgrade_uvx_only_refreshes_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upgrade_mod, "detect_install_method", lambda: UVX)
    calls = _recording_run(monkeypatch)

    result = CliRunner().invoke(app, ["upgrade"])

    assert result.exit_code == 0
    assert "uvx" in result.output
    assert calls == [SETUP]


def test_upgrade_nonzero_exit_raises_and_skips_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upgrade_mod, "detect_install_method", lambda: PIPX)
    calls = _recording_run(monkeypatch, {"upgrade": 1})

    result = CliRunner().invoke(app, ["upgrade"])

    assert result.exit_code != 0
    assert "status 1" in result.output
    assert calls == [["pipx", "upgrade", "mneva"]]


def test_failed_setup_refresh_says_the_upgrade_itself_worked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(upgrade_mod, "detect_install_method", lambda: PIPX)
    _recording_run(monkeypatch, {"setup": 1})

    result = CliRunner().invoke(app, ["upgrade"])

    assert result.exit_code != 0
    assert "mneva was updated" in result.output
    assert "mneva setup" in result.output


def test_upgrade_missing_tool_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upgrade_mod, "detect_install_method", lambda: UV_TOOL)

    def _fake_run(*_a: object, **_k: object) -> None:
        raise FileNotFoundError("uv not found")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = CliRunner().invoke(app, ["upgrade"])
    assert result.exit_code != 0
    assert "could not find 'uv'" in result.output
    assert "uv tool upgrade mneva" in result.output
