"""CLI-level tests for the Obsidian vault integration.

Covers `mneva config set-vault`, `mneva config get-vault`,
`mneva config unset-vault`, `mneva sync-vault`, and the vault-mirror
behaviour of `mneva capture`.
"""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from mneva.cli import app


def _make_vault(tmp_path: Path, name: str = "my-vault") -> Path:
    vault = tmp_path / name
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    return vault


def test_config_set_vault_rejects_non_vault_path(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    plain = tmp_path / "not-a-vault"
    plain.mkdir()
    result = runner.invoke(app, ["config", "set-vault", str(plain)])
    assert result.exit_code != 0
    assert "not an Obsidian vault" in result.output


def test_config_set_then_get_vault_round_trip(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    vault = _make_vault(tmp_path)
    set_result = runner.invoke(app, ["config", "set-vault", str(vault)])
    assert set_result.exit_code == 0, set_result.output
    assert "vault set" in set_result.output

    get_result = runner.invoke(app, ["config", "get-vault"])
    assert get_result.exit_code == 0
    assert str(vault.resolve()) in get_result.output

    cfg = json.loads((tmp_mneva_home / "config.json").read_text())
    assert cfg["vault_path"] == str(vault.resolve())


def test_config_unset_vault_clears_config(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    vault = _make_vault(tmp_path)
    runner.invoke(app, ["config", "set-vault", str(vault)])
    result = runner.invoke(app, ["config", "unset-vault"])
    assert result.exit_code == 0
    cfg = json.loads((tmp_mneva_home / "config.json").read_text())
    assert cfg["vault_path"] is None


def test_capture_mirrors_to_vault_when_configured(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    vault = _make_vault(tmp_path)
    runner.invoke(app, ["config", "set-vault", str(vault)])
    result = runner.invoke(
        app,
        ["capture", "--scope", "demo", "--lifespan", "permanent", "vault round-trip"],
    )
    assert result.exit_code == 0, result.output
    record_id = result.output.strip().splitlines()[-1]
    # Local store has it
    assert (tmp_mneva_home / "store" / f"{record_id}.md").exists()
    # Vault has it under mneva/<scope>/<id>.md
    vault_file = vault / "mneva" / "demo" / f"{record_id}.md"
    assert vault_file.exists()
    assert "vault round-trip" in vault_file.read_text(encoding="utf-8")


def test_capture_succeeds_when_vault_unconfigured(
    tmp_mneva_home: Path,
) -> None:
    """Regression: vault is opt-in. capture must work without one."""
    runner = CliRunner()
    runner.invoke(app, ["init"])
    result = runner.invoke(
        app,
        ["capture", "--scope", "demo", "--lifespan", "permanent", "no-vault path"],
    )
    assert result.exit_code == 0, result.output


def test_sync_vault_requires_vault_configured(tmp_mneva_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["sync-vault"])
    assert result.exit_code != 0
    assert "no vault configured" in result.output


def test_sync_vault_round_trip(tmp_mneva_home: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init"])
    vault = _make_vault(tmp_path)
    runner.invoke(app, ["config", "set-vault", str(vault)])
    runner.invoke(
        app,
        ["capture", "--scope", "demo", "--lifespan", "permanent", "round-trip body"],
    )
    # Drop the local copy to prove sync repopulates it
    for md in (tmp_mneva_home / "store").glob("*.md"):
        md.unlink()
    result = runner.invoke(app, ["sync-vault"])
    assert result.exit_code == 0, result.output
    assert "imported: 1" in result.output
    assert "skipped: 0" in result.output
    restored = list((tmp_mneva_home / "store").glob("*.md"))
    assert len(restored) == 1
    assert "round-trip body" in restored[0].read_text(encoding="utf-8")
