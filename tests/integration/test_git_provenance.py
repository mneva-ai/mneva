"""End-to-end guards for git-aware memory.

The failure modes here are all silent: memories that vanish from search,
provenance that gets wiped by a round trip, a column that quietly blanks on
reindex. Counts alone catch none of them, so every test below asserts on
behaviour a user would notice.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from click.testing import CliRunner

from mneva.cli import app
from mneva.indexer import Indexer
from mneva.store import Record, read_record, write_record

pytestmark = pytest.mark.integration


@contextmanager
def chdir(path: Path) -> Iterator[None]:
    """Run a block with the process cwd set to *path*."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _capture(cwd: Path, scope: str, body: str, *extra: str) -> str:
    runner = CliRunner()
    with chdir(cwd):
        result = runner.invoke(app, ["capture", "--scope", scope, *extra, body])
    assert result.exit_code == 0, result.output
    return result.output.strip()


def _search(cwd: Path, query: str, *extra: str) -> str:
    runner = CliRunner()
    with chdir(cwd):
        result = runner.invoke(app, ["search", query, *extra])
    assert result.exit_code == 0, result.output
    return result.output


def test_capture_inside_a_repo_records_provenance(
    tmp_mneva_home: Path, make_git_repo: Callable[..., Path]
) -> None:
    repo = make_git_repo("proj", remote="git@github.com:mneva-ai/mneva.git")
    record_id = _capture(repo, "proj", "decision: use sqlite for the index")

    rec = read_record(record_id, home=tmp_mneva_home)
    assert rec.repo == "github.com/mneva-ai/mneva"
    assert Path(rec.repo_path or "").resolve() == repo.resolve()
    assert rec.branch is not None
    assert rec.commit_sha is not None


def test_capture_outside_a_repo_still_works(tmp_mneva_home: Path, tmp_path: Path) -> None:
    """Provenance is a bonus, never a precondition for capturing."""
    plain = tmp_path / "no-repo"
    plain.mkdir()
    record_id = _capture(plain, "misc", "a thought with no project")
    rec = read_record(record_id, home=tmp_mneva_home)
    assert rec.repo is None
    assert rec.commit_sha is None


def test_no_git_flag_opts_out(
    tmp_mneva_home: Path, make_git_repo: Callable[..., Path]
) -> None:
    """Privacy escape hatch: repo_path exposes local directory layout."""
    repo = make_git_repo("private", remote="git@github.com:o/secret.git")
    record_id = _capture(repo, "p", "sensitive note", "--no-git")
    rec = read_record(record_id, home=tmp_mneva_home)
    assert rec.repo is None
    assert rec.repo_path is None


def test_search_hides_other_repos_but_keeps_unscoped_memories(
    tmp_mneva_home: Path, make_git_repo: Callable[..., Path], tmp_path: Path
) -> None:
    """The core retrieval promise, and the backward-compat guarantee together."""
    repo_a = make_git_repo("alpha", remote="git@github.com:o/alpha.git")
    repo_b = make_git_repo("beta", remote="git@github.com:o/beta.git")
    plain = tmp_path / "elsewhere"
    plain.mkdir()

    _capture(repo_a, "s", "widget alpha detail")
    _capture(repo_b, "s", "widget beta detail")
    _capture(plain, "s", "widget unscoped detail")

    from_a = _search(repo_a, "widget")
    assert "alpha detail" in from_a
    assert "beta detail" not in from_a
    # A memory belonging to no repo is relevant everywhere.
    assert "unscoped detail" in from_a

    everything = _search(repo_a, "widget", "--all-repos")
    assert "beta detail" in everything


def test_pre_v03_records_remain_visible_after_upgrade(
    tmp_mneva_home: Path, make_git_repo: Callable[..., Path]
) -> None:
    """Hard backward-compat rule.

    Every record written before v0.3 has repo = NULL. A strict `repo = ?`
    filter would make a user's entire history disappear from default search
    the moment they upgraded.
    """
    legacy = Record(
        id="legacy001",
        scope="old",
        lifespan="permanent",
        tool="cli",
        body="widget knowledge from before the upgrade",
    )
    write_record(legacy, home=tmp_mneva_home)
    Indexer(tmp_mneva_home / "mneva.sqlite").rebuild()

    repo = make_git_repo("newproj", remote="git@github.com:o/newproj.git")
    assert "from before the upgrade" in _search(repo, "widget")


def test_reindex_preserves_repo_isolation(
    tmp_mneva_home: Path, make_git_repo: Callable[..., Path]
) -> None:
    """`rebuild()` has its own INSERT; if it omits repo, filtering silently dies.

    Asserting counts would not catch this -- the rows are all still there, they
    just lose the column that makes them separable.
    """
    repo_a = make_git_repo("alpha", remote="git@github.com:o/alpha.git")
    repo_b = make_git_repo("beta", remote="git@github.com:o/beta.git")
    _capture(repo_a, "s", "gadget alpha detail")
    _capture(repo_b, "s", "gadget beta detail")

    runner = CliRunner()
    with chdir(repo_a):
        assert runner.invoke(app, ["reindex"]).exit_code == 0

    from_a = _search(repo_a, "gadget")
    assert "alpha detail" in from_a
    assert "beta detail" not in from_a


def test_vault_round_trip_preserves_provenance(
    tmp_mneva_home: Path, make_git_repo: Callable[..., Path], tmp_path: Path
) -> None:
    """capture -> vault -> sync-vault must not strip git fields.

    sync_from_vault overwrites the local store, so a dropped field here is
    silent data loss rather than a missing display value.
    """
    from mneva.vault import sync_from_vault, write_to_vault

    repo = make_git_repo("proj", remote="git@github.com:o/proj.git")
    record_id = _capture(repo, "proj", "architecture decision worth keeping")
    original = read_record(record_id, home=tmp_mneva_home)
    assert original.repo == "github.com/o/proj"

    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    note_path = write_to_vault(original, vault)

    # The Obsidian note itself must carry the provenance, not just the store.
    note_text = note_path.read_text(encoding="utf-8")
    assert "github.com/o/proj" in note_text
    assert "commit_sha" in note_text

    sync_from_vault(vault, tmp_mneva_home)
    after = read_record(record_id, home=tmp_mneva_home)
    assert after.repo == original.repo
    assert after.commit_sha == original.commit_sha
    assert after.branch == original.branch
    assert after.repo_path == original.repo_path


def test_frontmatter_stays_clean_without_provenance(tmp_mneva_home: Path) -> None:
    """No `repo: null` clutter in notes the user reads in Obsidian."""
    rec = Record(id="clean1", scope="s", lifespan="permanent", tool="cli", body="text")
    path = write_record(rec, home=tmp_mneva_home)
    text = path.read_text(encoding="utf-8")
    for absent in ("repo:", "repo_path:", "branch:", "commit_sha:"):
        assert absent not in text


def test_status_reports_provenance_coverage(
    tmp_mneva_home: Path, make_git_repo: Callable[..., Path], tmp_path: Path
) -> None:
    """The only signal that MCP clients are actually passing repo_path."""
    repo = make_git_repo("proj", remote="git@github.com:o/proj.git")
    plain = tmp_path / "nowhere"
    plain.mkdir()
    _capture(repo, "s", "has provenance")
    _capture(plain, "s", "has none")

    runner = CliRunner()
    with chdir(repo):
        out = runner.invoke(app, ["status"]).output
    assert "with repo provenance: 1 / 2" in out
    assert "github.com/o/proj" in out
