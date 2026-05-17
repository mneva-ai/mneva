from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from mneva.config import Config, ConfigError, generate_token, load_config, save_config
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


def test_load_raises_config_error_when_missing(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    with pytest.raises(ConfigError) as exc:
        load_config(home)
    assert "run `mneva init`" in str(exc.value)


def test_load_raises_config_error_on_malformed_json(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    (home / "config.json").write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(home)
    assert "not valid JSON" in str(exc.value)


def test_load_raises_config_error_on_non_object_root(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    (home / "config.json").write_text('["not", "an", "object"]', encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(home)
    assert "JSON object" in str(exc.value)


def test_load_raises_config_error_on_unknown_field(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    (home / "config.json").write_text(
        '{"token": "a", "totally_unknown_field": 42}', encoding="utf-8"
    )
    with pytest.raises(ConfigError) as exc:
        load_config(home)
    assert "unexpected or missing fields" in str(exc.value)


def test_save_serialises_known_fields(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    save_config(Config(token="a" * 32, port=9999), home)
    data = json.loads((home / "config.json").read_text())
    assert data["port"] == 9999
    assert data["token"] == "a" * 32
