from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from mneva import setup
from mneva.cli import app


class FakeAgents:
    """Stands in for the `claude` and `codex` CLIs.

    `registered` holds the executables that already have mneva; `broken`
    holds the ones whose `mcp add` fails.
    """

    def __init__(
        self,
        installed: tuple[str, ...] = ("claude", "codex"),
        registered: tuple[str, ...] = (),
        broken: tuple[str, ...] = (),
    ) -> None:
        self.installed = installed
        self.registered = set(registered)
        self.broken = broken
        self.calls: list[list[str]] = []

    def which(self, name: str) -> str | None:
        return f"/bin/{name}" if name in self.installed else None

    def run(self, argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        exe = Path(argv[0]).name
        action = argv[2]
        if action == "get":
            code = 0 if exe in self.registered else 1
        elif exe in self.broken:
            return subprocess.CompletedProcess(argv, 1, "", "config file is locked\n")
        else:
            self.registered.add(exe)
            code = 0
        return subprocess.CompletedProcess(argv, code, "", "")

    def adds(self) -> list[str]:
        return [Path(c[0]).name for c in self.calls if c[2] == "add"]


@pytest.fixture
def agents(monkeypatch: pytest.MonkeyPatch) -> FakeAgents:
    fake = FakeAgents()
    monkeypatch.setattr(setup.shutil, "which", fake.which)
    monkeypatch.setattr(setup.subprocess, "run", fake.run)
    # Never write the real browser registry from tests.
    monkeypatch.setattr(
        setup.native_host, "register", lambda argv, dry_run=False: "Browser bridge: registered"
    )
    return fake


def test_setup_registers_the_browser_bridge_and_says_how_to_load_the_extension(
    tmp_mneva_home: Path, agents: FakeAgents
) -> None:
    result = CliRunner().invoke(app, ["setup"])

    assert result.exit_code == 0, result.output
    assert "Browser bridge: registered" in result.output
    assert "Load unpacked" in result.output
    assert str(setup.native_host.EXTENSION_DIR) in result.output


def test_failing_browser_bridge_does_not_stop_the_agents(
    tmp_mneva_home: Path, agents: FakeAgents, monkeypatch: pytest.MonkeyPatch
) -> None:
    def locked(argv: list[str], dry_run: bool = False) -> str:
        raise PermissionError("registry is locked")

    monkeypatch.setattr(setup.native_host, "register", locked)

    result = CliRunner().invoke(app, ["setup"])

    assert result.exit_code != 0
    assert "Browser bridge: failed (registry is locked)" in result.output
    assert "Codex: added" in result.output


def test_setup_registers_every_installed_agent(tmp_mneva_home: Path, agents: FakeAgents) -> None:
    result = CliRunner().invoke(app, ["setup"])

    assert result.exit_code == 0, result.output
    assert agents.adds() == ["claude", "codex"]
    assert "Claude Code: added" in result.output
    assert "Codex: added" in result.output


def test_setup_twice_changes_nothing_the_second_time(
    tmp_mneva_home: Path, agents: FakeAgents
) -> None:
    CliRunner().invoke(app, ["setup"])
    template = tmp_mneva_home / setup.PROFILE_TEMPLATE_NAME
    template.write_text("my own edits", encoding="utf-8")
    agents.calls.clear()

    result = CliRunner().invoke(app, ["setup"])

    assert result.exit_code == 0, result.output
    assert agents.adds() == []
    assert "already registered" in result.output
    assert template.read_text(encoding="utf-8") == "my own edits"


def test_setup_skips_agents_that_are_not_installed(
    tmp_mneva_home: Path, agents: FakeAgents
) -> None:
    agents.installed = ("claude",)

    result = CliRunner().invoke(app, ["setup"])

    assert result.exit_code == 0, result.output
    assert agents.adds() == ["claude"]
    assert "Codex: not found" in result.output


def test_setup_dry_run_changes_nothing(tmp_mneva_home: Path, agents: FakeAgents) -> None:
    result = CliRunner().invoke(app, ["setup", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert agents.adds() == []
    assert "would run" in result.output
    assert not (tmp_mneva_home / setup.PROFILE_TEMPLATE_NAME).exists()


def test_setup_writes_profile_template(tmp_mneva_home: Path, agents: FakeAgents) -> None:
    result = CliRunner().invoke(app, ["setup"])

    template = tmp_mneva_home / setup.PROFILE_TEMPLATE_NAME
    assert result.exit_code == 0, result.output
    assert "## Who I am" in template.read_text(encoding="utf-8")
    assert str(template) in result.output


def test_one_failing_agent_does_not_stop_the_other(
    tmp_mneva_home: Path, agents: FakeAgents
) -> None:
    agents.broken = ("claude",)

    result = CliRunner().invoke(app, ["setup"])

    assert result.exit_code != 0
    assert "Claude Code: failed" in result.output
    assert "config file is locked" in result.output
    assert "Codex: added" in result.output
