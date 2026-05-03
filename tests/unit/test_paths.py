from __future__ import annotations

from pathlib import Path

import pytest

from mneva.paths import ensure_home, mneva_home


def test_default_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MNEVA_HOME", raising=False)
    assert mneva_home() == Path.home() / ".mneva"


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MNEVA_HOME", str(tmp_path))
    assert mneva_home() == tmp_path


def test_ensure_home_creates_subdirs(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    assert home == tmp_mneva_home
    for sub in ("store", "index", "adr", "templates"):
        assert (home / sub).is_dir()
