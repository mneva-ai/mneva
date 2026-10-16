from __future__ import annotations

import json
from pathlib import Path

import pytest

from mneva import native_host

LAUNCH = ["C:/py/python.exe", "-m", "mneva.native_host"]


@pytest.fixture
def fake_registry(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    # Never touch the real HKCU from tests.
    registry: dict[str, str] = {}
    monkeypatch.setattr(native_host.sys, "platform", "win32")
    monkeypatch.setattr(native_host, "_registry_get", registry.get)
    monkeypatch.setattr(native_host, "_registry_set", registry.__setitem__)
    return registry


def test_extension_id_is_derived_from_the_committed_public_key() -> None:
    ids = native_host.extension_ids()

    assert ids[0] == "bkffkclmkcjonpablhoeoaejmkkdbchh"
    assert all(len(i) == 32 and set(i) <= set("abcdefghijklmnop") for i in ids)


def test_windows_registers_chrome_edge_and_chromium(
    tmp_mneva_home: Path, fake_registry: dict[str, str]
) -> None:
    line = native_host.register(LAUNCH)

    manifest_path = tmp_mneva_home / "native-host" / f"{native_host.HOST_NAME}.json"
    assert set(fake_registry.values()) == {str(manifest_path)}
    assert {k.split("\\")[1] for k in fake_registry} == {"Google", "Microsoft", "Chromium"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["allowed_origins"] == ["chrome-extension://bkffkclmkcjonpablhoeoaejmkkdbchh/"]
    launcher = Path(manifest["path"])
    assert launcher.name.endswith(".bat")
    assert launcher.read_text(encoding="utf-8").startswith("@echo off")
    assert "C:/py/python.exe -m mneva.native_host" in launcher.read_text(encoding="utf-8")
    assert "registered for Chrome, Edge, Chromium" in line


def test_second_run_changes_nothing(tmp_mneva_home: Path, fake_registry: dict[str, str]) -> None:
    native_host.register(LAUNCH)

    assert "already registered" in native_host.register(LAUNCH)


def test_dry_run_writes_nothing(tmp_mneva_home: Path, fake_registry: dict[str, str]) -> None:
    line = native_host.register(LAUNCH, dry_run=True)

    assert "would register" in line
    assert fake_registry == {}
    assert not (tmp_mneva_home / "native-host").exists()


def test_linux_registers_only_installed_browsers(
    tmp_mneva_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_host.sys, "platform", "linux")
    monkeypatch.setattr(native_host.Path, "home", lambda: tmp_path)
    (tmp_path / ".config" / "google-chrome").mkdir(parents=True)

    line = native_host.register(LAUNCH)

    hosts = tmp_path / ".config" / "google-chrome" / "NativeMessagingHosts"
    manifest = json.loads((hosts / f"{native_host.HOST_NAME}.json").read_text(encoding="utf-8"))
    assert Path(manifest["path"]).read_text(encoding="utf-8").startswith("#!/bin/sh\nexec ")
    assert not (tmp_path / ".config" / "microsoft-edge").exists()
    assert line.endswith("for Chrome")
