from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def tmp_mneva_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated $MNEVA_HOME pointing at a tmp dir (`<tmp>/.mneva`)."""
    home = tmp_path / ".mneva"
    home.mkdir()
    monkeypatch.setenv("MNEVA_HOME", str(home))
    return home


@pytest.fixture
def make_git_repo(tmp_path: Path) -> Callable[..., Path]:
    """Factory for real git repos to test provenance against.

    Uses LOCAL git config so it never depends on the runner having a global
    user.name / user.email (CI images generally do not).
    """

    def _make(name: str, *, remote: str | None = None) -> Path:
        path = tmp_path / name
        path.mkdir(parents=True, exist_ok=True)

        def git(*args: str) -> None:
            subprocess.run(  # noqa: S603
                ["git", *args], cwd=path, check=True, capture_output=True  # noqa: S607
            )

        git("init", "-q")
        git("config", "user.email", "test@mneva.invalid")
        git("config", "user.name", "mneva test")
        if remote is not None:
            git("remote", "add", "origin", remote)
        (path / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        git("add", "README.md")
        git("commit", "-q", "-m", "initial")
        return path

    return _make
