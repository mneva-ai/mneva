"""Tests for git context detection.

Every degradation path matters here: `mneva capture` must never fail because
of git, and a wrong repo identity is worse than no identity (it silently
misfiles memories under someone else's project).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mneva.gitctx import GitContext, detect, normalize_remote_url


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args], cwd=cwd, check=True, capture_output=True  # noqa: S607
    )


def _make_repo(path: Path, *, remote: str | None = None, commit: bool = True) -> Path:
    """Init a git repo with LOCAL user config (never depend on the runner's global config)."""
    path.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", cwd=path)
    _git("config", "user.email", "test@mneva.invalid", cwd=path)
    _git("config", "user.name", "mneva test", cwd=path)
    if remote is not None:
        _git("remote", "add", "origin", remote, cwd=path)
    if commit:
        (path / "README.md").write_text("hello\n", encoding="utf-8")
        _git("add", "README.md", cwd=path)
        _git("commit", "-q", "-m", "initial", cwd=path)
    return path


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("git@github.com:mneva-ai/mneva.git", "github.com/mneva-ai/mneva"),
        ("https://github.com/mneva-ai/mneva.git", "github.com/mneva-ai/mneva"),
        ("https://github.com/mneva-ai/mneva", "github.com/mneva-ai/mneva"),
        ("ssh://git@github.com/mneva-ai/mneva.git", "github.com/mneva-ai/mneva"),
        ("https://user:token@github.com/mneva-ai/mneva.git", "github.com/mneva-ai/mneva"),
        ("https://github.com/mneva-ai/mneva/", "github.com/mneva-ai/mneva"),
        # Case must fold: github.com/Foo/Bar and github.com/foo/bar are the same
        # repo, and a case mismatch would silently drop records from the filter.
        ("git@github.com:Mneva-AI/Mneva.git", "github.com/mneva-ai/mneva"),
        ("git@gitlab.com:group/sub/proj.git", "gitlab.com/group/sub/proj"),
    ],
)
def test_normalize_remote_url_folds_equivalent_forms(raw: str, expected: str) -> None:
    assert normalize_remote_url(raw) == expected


def test_detect_in_repo_with_remote(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "proj", remote="git@github.com:mneva-ai/mneva.git")
    ctx = detect(repo)
    assert isinstance(ctx, GitContext)
    assert ctx.repo == "github.com/mneva-ai/mneva"
    # Compare resolved paths: git returns forward slashes on Windows, and on
    # macOS tmp_path (/var/...) resolves through a symlink to /private/var/...
    assert Path(ctx.repo_path).resolve() == repo.resolve()
    assert ctx.branch is not None and ctx.branch != "HEAD"
    assert ctx.commit_sha is not None and len(ctx.commit_sha) == 40


def test_detect_from_subdirectory_finds_the_toplevel(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "proj", remote="git@github.com:o/r.git")
    nested = repo / "src" / "deep"
    nested.mkdir(parents=True)
    ctx = detect(nested)
    assert ctx is not None
    assert Path(ctx.repo_path).resolve() == repo.resolve()


def test_detect_outside_a_repo_returns_none(tmp_path: Path) -> None:
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    assert detect(plain) is None


def test_repo_without_remote_falls_back_to_local_name(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "solo-project", remote=None)
    ctx = detect(repo)
    assert ctx is not None
    assert ctx.repo == "local:solo-project"


def test_repo_without_commits_still_reports_identity(tmp_path: Path) -> None:
    """An empty repo has no HEAD; that must not lose repo/branch identity."""
    repo = _make_repo(tmp_path / "empty", remote="git@github.com:o/r.git", commit=False)
    ctx = detect(repo)
    assert ctx is not None
    assert ctx.repo == "github.com/o/r"
    assert ctx.commit_sha is None


def test_detached_head_records_no_branch(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "detached", remote="git@github.com:o/r.git")
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git("checkout", "-q", "--detach", sha, cwd=repo)
    ctx = detect(repo)
    assert ctx is not None
    assert ctx.branch is None
    assert ctx.commit_sha == sha


def test_missing_git_binary_degrades_to_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No git on PATH must not raise -- capture has to keep working."""
    repo = _make_repo(tmp_path / "proj", remote="git@github.com:o/r.git")

    def boom(*a: object, **kw: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", boom)
    assert detect(repo) is None


def test_git_timeout_degrades_to_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """git can hang on network-mounted dirs; a hang must not hang capture."""
    repo = _make_repo(tmp_path / "proj", remote="git@github.com:o/r.git")

    def slow(*a: object, **kw: object) -> None:
        raise subprocess.TimeoutExpired(cmd="git", timeout=5)

    monkeypatch.setattr(subprocess, "run", slow)
    assert detect(repo) is None


def test_detect_on_missing_directory_returns_none(tmp_path: Path) -> None:
    assert detect(tmp_path / "does-not-exist") is None
