from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from mneva.config import Config, generate_token, load_config, save_config
from mneva.paths import ensure_home


def test_generate_token_is_32_hex_chars() -> None:
    t = generate_token()
    assert len(t) == 32
    int(t, 16)


def test_save_then_load_roundtrip(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    cfg = Config(token="deadbeef" * 4, port=7432)
    save_config(cfg, home)
    assert load_config(home) == cfg


def test_save_writes_0600_mode(tmp_mneva_home: Path) -> None:
    if sys.platform.startswith("win"):
        pytest.skip("POSIX permission bits not enforced on Windows NTFS")
    home = ensure_home()
    save_config(Config(token="x" * 32), home)
    mode = stat.S_IMODE(os.stat(home / "config.json").st_mode)
    assert mode == 0o600


def test_load_raises_when_missing(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    with pytest.raises(FileNotFoundError):
        load_config(home)


def test_save_serialises_known_fields(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    save_config(Config(token="a" * 32, port=9999), home)
    data = json.loads((home / "config.json").read_text())
    assert data["port"] == 9999
    assert data["token"] == "a" * 32
