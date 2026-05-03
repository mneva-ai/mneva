from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_mneva_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated $MNEVA_HOME pointing at a tmp dir (`<tmp>/.mneva`)."""
    home = tmp_path / ".mneva"
    home.mkdir()
    monkeypatch.setenv("MNEVA_HOME", str(home))
    return home
