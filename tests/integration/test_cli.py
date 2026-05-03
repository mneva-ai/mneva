from __future__ import annotations

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
