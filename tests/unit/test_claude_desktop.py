from __future__ import annotations

import json
from pathlib import Path

from mneva import claude_desktop

SERVER = ["C:/py/python.exe", "-m", "mneva.mcp_server"]
ENTRY = {
    "command": "C:/py/python.exe",
    "args": ["-m", "mneva.mcp_server"],
    "env": {"MNEVA_MCP_CLIENT": "claude-desktop"},
}


def _config(folder: Path) -> Path:
    return folder / claude_desktop.CONFIG_NAME


def test_config_dir_per_platform(tmp_path: Path) -> None:
    env = {"APPDATA": str(tmp_path / "Roaming")}
    assert claude_desktop.config_dir("win32", env, tmp_path) == tmp_path / "Roaming" / "Claude"
    assert claude_desktop.config_dir("darwin", env, tmp_path) == (
        tmp_path / "Library" / "Application Support" / "Claude"
    )
    # No Claude desktop app exists for Linux.
    assert claude_desktop.config_dir("linux", env, tmp_path) is None


def test_no_claude_folder_means_not_installed_and_nothing_is_created(tmp_path: Path) -> None:
    folder = tmp_path / "Claude"

    ok, message = claude_desktop.register(SERVER, dry_run=False, folder=folder)

    assert ok and "not found" in message
    assert not folder.exists()


def test_no_supported_platform_is_skipped() -> None:
    ok, message = claude_desktop.register(SERVER, dry_run=False, folder=None)

    assert ok and "skipped" in message


def test_missing_file_in_existing_folder_is_created(tmp_path: Path) -> None:
    ok, message = claude_desktop.register(SERVER, dry_run=False, folder=tmp_path)

    assert ok
    assert json.loads(_config(tmp_path).read_text(encoding="utf-8")) == {
        "mcpServers": {"mneva": ENTRY}
    }
    assert "restart" in message.lower() or "reopen" in message.lower()


def test_other_servers_and_settings_are_kept(tmp_path: Path) -> None:
    other = {"command": "npx", "args": ["-y", "some-server"]}
    _config(tmp_path).write_text(
        json.dumps({"mcpServers": {"other": other}, "globalShortcut": "Ctrl+Space"}),
        encoding="utf-8",
    )

    ok, _ = claude_desktop.register(SERVER, dry_run=False, folder=tmp_path)

    assert ok
    assert json.loads(_config(tmp_path).read_text(encoding="utf-8")) == {
        "mcpServers": {"other": other, "mneva": ENTRY},
        "globalShortcut": "Ctrl+Space",
    }


def test_existing_entry_is_left_unchanged(tmp_path: Path) -> None:
    original = json.dumps({"mcpServers": {"mneva": {"command": "uvx", "args": []}}})
    _config(tmp_path).write_text(original, encoding="utf-8")

    ok, message = claude_desktop.register(SERVER, dry_run=False, folder=tmp_path)

    assert ok and "already" in message
    assert _config(tmp_path).read_text(encoding="utf-8") == original


def test_invalid_json_is_left_byte_for_byte_and_the_entry_is_shown(tmp_path: Path) -> None:
    original = b'{"mcpServers": {,,}\r\n'
    _config(tmp_path).write_bytes(original)

    ok, message = claude_desktop.register(SERVER, dry_run=False, folder=tmp_path)

    assert not ok
    assert _config(tmp_path).read_bytes() == original
    assert '"MNEVA_MCP_CLIENT": "claude-desktop"' in message


def test_mcp_servers_of_the_wrong_shape_is_not_overwritten(tmp_path: Path) -> None:
    original = json.dumps({"mcpServers": ["not", "an", "object"]})
    _config(tmp_path).write_text(original, encoding="utf-8")

    ok, _ = claude_desktop.register(SERVER, dry_run=False, folder=tmp_path)

    assert not ok
    assert _config(tmp_path).read_text(encoding="utf-8") == original


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    ok, message = claude_desktop.register(SERVER, dry_run=True, folder=tmp_path)

    assert ok and "would" in message
    assert not _config(tmp_path).exists()


def test_non_ascii_content_survives(tmp_path: Path) -> None:
    _config(tmp_path).write_text(
        json.dumps({"mcpServers": {}, "note": "我的设置"}, ensure_ascii=False), encoding="utf-8"
    )

    claude_desktop.register(SERVER, dry_run=False, folder=tmp_path)

    assert json.loads(_config(tmp_path).read_text(encoding="utf-8"))["note"] == "我的设置"
