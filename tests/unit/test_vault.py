from __future__ import annotations

from pathlib import Path

import frontmatter
import pytest

from mneva.paths import ensure_home
from mneva.store import Record, iter_records
from mneva.vault import (
    SyncResult,
    VaultError,
    detect_vault,
    sync_from_vault,
    vault_record_path,
    write_to_vault,
)


def _make_vault(tmp_path: Path) -> Path:
    """Create a minimal directory that detect_vault accepts."""
    vault = tmp_path / "my-vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    return vault


def _record(scope: str = "demo", body: str = "hello", rid: str = "abc123") -> Record:
    return Record(
        id=rid, scope=scope, lifespan="permanent", tool="cli", body=body, source=None
    )


def test_detect_vault_accepts_dir_with_dot_obsidian(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    assert detect_vault(vault) is True


def test_detect_vault_rejects_dir_without_dot_obsidian(tmp_path: Path) -> None:
    plain = tmp_path / "not-a-vault"
    plain.mkdir()
    assert detect_vault(plain) is False


def test_detect_vault_rejects_non_directory(tmp_path: Path) -> None:
    nope = tmp_path / "missing"
    assert detect_vault(nope) is False


def test_vault_record_path_layout(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    rec = _record(scope="project-x", rid="deadbeef00112233")
    p = vault_record_path(rec, vault)
    assert p == vault / "mneva" / "project-x" / "deadbeef00112233.md"


def test_write_to_vault_round_trips_frontmatter(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    rec = _record(body="decision: use SQLite over Postgres")
    target = write_to_vault(rec, vault)
    assert target.exists()
    post = frontmatter.loads(target.read_text(encoding="utf-8"))
    assert post["mneva_id"] == rec.id
    assert post["scope"] == rec.scope
    assert post["lifespan"] == rec.lifespan
    assert post["tool"] == rec.tool
    assert post.content == rec.body


def test_write_to_vault_raises_when_path_is_not_a_vault(tmp_path: Path) -> None:
    plain = tmp_path / "not-a-vault"
    plain.mkdir()
    rec = _record()
    with pytest.raises(VaultError) as exc:
        write_to_vault(rec, plain)
    assert ".obsidian/" in str(exc.value)


def test_sync_from_vault_imports_mneva_notes(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    vault = _make_vault(tmp_path)
    home = ensure_home()
    rec = _record(rid="aa11", body="indexed via vault round-trip")
    write_to_vault(rec, vault)

    result = sync_from_vault(vault, home)
    assert isinstance(result, SyncResult)
    assert result.imported == 1
    assert result.skipped == 0

    records = list(iter_records(home=home))
    assert any(r.id == "aa11" and "vault round-trip" in r.body for r in records)


def test_sync_from_vault_skips_notes_without_mneva_id(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    vault = _make_vault(tmp_path)
    home = ensure_home()
    foreign = vault / "mneva" / "alpha" / "user-note.md"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("# Just a note I wrote myself\n", encoding="utf-8")

    result = sync_from_vault(vault, home)
    assert result.imported == 0
    assert result.skipped == 1
    assert list(iter_records(home=home)) == []


def test_sync_from_vault_handles_missing_mneva_subdir(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    """A vault with no mneva/ subdir should sync cleanly with 0/0 counts."""
    vault = _make_vault(tmp_path)
    home = ensure_home()
    result = sync_from_vault(vault, home)
    assert result == SyncResult(imported=0, skipped=0)


def test_sync_from_vault_raises_on_invalid_vault(
    tmp_mneva_home: Path, tmp_path: Path
) -> None:
    plain = tmp_path / "not-a-vault"
    plain.mkdir()
    with pytest.raises(VaultError):
        sync_from_vault(plain, ensure_home())
