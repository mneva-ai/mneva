from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from mneva.cli import app


def test_version_flag_prints_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0a1" in result.output


def test_help_lists_core_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("init", "capture", "search", "status", "forget", "config", "serve"):
        assert cmd in result.output


def test_init_creates_home_token_and_bootstrap(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert (tmp_mneva_home / "config.json").exists()
    cfg = json.loads((tmp_mneva_home / "config.json").read_text())
    assert len(cfg["token"]) == 32
    assert cfg["port"] == 7432
    assert (tmp_mneva_home / "bootstrap.md").exists()
    assert "Mneva Bootstrap" in (tmp_mneva_home / "bootstrap.md").read_text()
    assert "Token (save this — shown only on init)" in result.output
    assert cfg["token"] in result.output


def test_init_is_idempotent_but_does_not_overwrite_token(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    cfg_before = json.loads((tmp_mneva_home / "config.json").read_text())
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    cfg_after = json.loads((tmp_mneva_home / "config.json").read_text())
    assert cfg_before["token"] == cfg_after["token"]


def test_capture_writes_record_from_argument(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    result = runner.invoke(
        app,
        ["capture", "--scope", "ticket-7", "--tool", "claude-code", "Hello world"],
    )
    assert result.exit_code == 0, result.output
    files = list((tmp_mneva_home / "store").glob("*.md"))
    assert len(files) == 1
    body = files[0].read_text()
    assert "Hello world" in body
    assert "scope: ticket-7" in body
    assert "tool: claude-code" in body


def test_capture_reads_stdin_when_body_is_dash(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    result = runner.invoke(
        app, ["capture", "--scope", "s", "-"], input="from stdin\n"
    )
    assert result.exit_code == 0, result.output
    files = list((tmp_mneva_home / "store").glob("*.md"))
    assert "from stdin" in files[0].read_text()


def test_search_returns_captured_record(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    runner.invoke(
        app,
        ["capture", "--scope", "s", "--lifespan", "permanent", "the brown fox jumps"],
    )
    result = runner.invoke(app, ["search", "brown fox"])
    assert result.exit_code == 0
    assert "brown fox" in result.output


def test_search_scope_filter(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    runner.invoke(app, ["capture", "--scope", "x", "--lifespan", "permanent", "alpha"])
    runner.invoke(app, ["capture", "--scope", "y", "--lifespan", "permanent", "alpha"])
    result = runner.invoke(app, ["search", "alpha", "--scope", "x"])
    assert result.exit_code == 0
    assert result.output.count("scope: x") == 1
    assert "scope: y" not in result.output


def test_status_reports_mode_and_count(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    runner.invoke(app, ["capture", "--scope", "s", "alpha"])
    runner.invoke(app, ["capture", "--scope", "s", "beta"])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "mode:" in result.output.lower()
    assert "count: 2" in result.output


def test_forget_requires_confirm_flag(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    out = runner.invoke(app, ["capture", "--scope", "s", "to-be-deleted"]).output.strip()
    record_id = out.splitlines()[-1]
    result = runner.invoke(app, ["forget", record_id])
    assert result.exit_code != 0
    result = runner.invoke(app, ["forget", record_id, "--confirm"])
    assert result.exit_code == 0
    assert (tmp_mneva_home / "store" / f"{record_id}.md").exists() is False
