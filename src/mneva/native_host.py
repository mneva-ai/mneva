"""native_host.py — the native messaging host behind the mneva browser extension.

Chrome and Edge start this process on demand when the extension asks for the
profile, and talk to it over stdio: each message is a 4-byte little-endian
length followed by that many bytes of UTF-8 JSON. It answers two requests,
`ping` and `get_brief`, and nothing else; it never writes to the store.
Every reply also carries the version of the extension copy `mneva setup`
installed, so an extension running older files can tell it should reload.

Every rule below is a silent total failure if broken, because the browser
just sees a dead host:
- stdio must be binary (on Windows, text mode turns \\n into \\r\\n inside
  the length prefix);
- stdout carries frames only, so diagnostics go to stderr;
- import only what the brief needs: mneva.cli reconfigures stdout at import,
  mneva.mcp_server writes to stderr on start.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shlex
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, BinaryIO

from mneva import __version__
from mneva.brief import DEFAULT_MAX_CHARS, PROFILE_SCOPE, render_brief
from mneva.paths import mneva_home

HOST_NAME = "org.mneva.brief"
EXTENSION_DIR = Path(__file__).parent / "extension"
# The Chrome Web Store rejects a manifest `key` and assigns its own ID, so a
# store build will have a second ID. Add it here once the listing exists.
STORE_EXTENSION_IDS: tuple[str, ...] = ()

# Per-user registration locations. Chromium is included so Playwright's
# bundled browser can exercise the extension end to end in tests.
_WINDOWS_REGISTRY_PARENTS = {
    "Chrome": r"Software\Google\Chrome\NativeMessagingHosts",
    "Edge": r"Software\Microsoft\Edge\NativeMessagingHosts",
    "Chromium": r"Software\Chromium\NativeMessagingHosts",
}
_MACOS_PROFILE_DIRS = {
    "Chrome": "Library/Application Support/Google/Chrome",
    "Edge": "Library/Application Support/Microsoft Edge",
    "Chromium": "Library/Application Support/Chromium",
}
_LINUX_PROFILE_DIRS = {
    "Chrome": ".config/google-chrome",
    "Edge": ".config/microsoft-edge",
    "Chromium": ".config/chromium",
}
# A real request is a few dozen bytes; anything near this is a broken stream.
_MAX_REQUEST_BYTES = 64 * 1024
_MAX_BRIEF_CHARS = 20_000


class _Unrecoverable(Exception):
    """The stream is out of sync; answer once and stop."""


def _binary_stdio() -> tuple[BinaryIO, BinaryIO]:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    return sys.stdin.buffer, sys.stdout.buffer


def read_message(stream: BinaryIO) -> Any:
    """Return the next decoded message, or None at end of input.

    Raises ValueError for a well-framed body that is not JSON (the stream is
    still in sync) and _Unrecoverable for a length that cannot be trusted.
    """
    header = stream.read(4)
    if len(header) < 4:
        return None
    (length,) = struct.unpack("<I", header)
    if length > _MAX_REQUEST_BYTES:
        raise _Unrecoverable(f"request of {length} bytes exceeds {_MAX_REQUEST_BYTES}")
    body = stream.read(length)
    if len(body) < length:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(stream: BinaryIO, message: dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(body)) + body)
    stream.flush()


def _bad_request(message: str) -> dict[str, Any]:
    return {"ok": False, "error": "bad_request", "message": message}


def installed_extension_version() -> str | None:
    """Version of the copy in the data root, the folder the browser loaded."""
    try:
        manifest = json.loads((mneva_home() / "extension" / "manifest.json").read_text("utf-8"))
    except (OSError, ValueError):
        return None
    version = manifest.get("version") if isinstance(manifest, dict) else None
    return version if isinstance(version, str) else None


def handle(message: Any) -> dict[str, Any]:
    reply = _answer(message)
    version = installed_extension_version()
    if version is not None:
        reply["extension_version"] = version
    return reply


def _answer(message: Any) -> dict[str, Any]:
    if not isinstance(message, dict):
        return _bad_request("expected a JSON object")
    kind = message.get("type")
    if kind == "ping":
        return {"ok": True, "version": __version__}
    if kind == "get_brief":
        requested = message.get("max_chars", DEFAULT_MAX_CHARS)
        if not isinstance(requested, int):
            return _bad_request("max_chars must be an integer")
        result = render_brief(max_chars=min(max(requested, 1), _MAX_BRIEF_CHARS))
        if result.included:
            return {"ok": True, "text": result.text, "records": len(result.included)}
        if result.skipped:
            return {"ok": False, "error": "too_small", "message": "No profile record fits."}
        return {
            "ok": False,
            "error": "no_profile",
            "message": (
                f"Your mneva profile is empty. Add records with: "
                f"mneva capture --scope {PROFILE_SCOPE} --lifespan permanent --no-git -"
            ),
        }
    return _bad_request(f"unknown request type {kind!r}")


def serve(stdin: BinaryIO, stdout: BinaryIO) -> None:
    while True:
        try:
            message = read_message(stdin)
        except _Unrecoverable as e:
            write_message(stdout, _bad_request(str(e)))
            return
        except ValueError:
            write_message(stdout, _bad_request("request is not UTF-8 JSON"))
            continue
        if message is None:  # EOF: the extension disconnected.
            return
        try:
            reply = handle(message)
        except Exception as e:  # one bad request must not kill the host
            print(f"mneva native host: {type(e).__name__}: {e}", file=sys.stderr)
            reply = {"ok": False, "error": "internal", "message": type(e).__name__}
        write_message(stdout, reply)


def main() -> None:
    serve(*_binary_stdio())


# ---------------------------------------------------------------- registration


def extension_id_from_key(public_key_b64: str) -> str:
    """Chrome's extension ID: first 128 bits of SHA-256(key), hex mapped to a-p."""
    digest = hashlib.sha256(base64.b64decode(public_key_b64)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(c, 16)) for c in digest)


def extension_ids() -> list[str]:
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))
    return [extension_id_from_key(manifest["key"]), *STORE_EXTENSION_IDS]


def _registry_get(path: str) -> str | None:
    if sys.platform != "win32":
        raise OSError("the registry exists only on Windows")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, "")
            return str(value)
    except OSError:
        return None


def _registry_set(path: str, value: str) -> None:
    if sys.platform != "win32":
        raise OSError("the registry exists only on Windows")
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, value)


def _write_if_changed(path: Path, content: bytes, *, dry_run: bool) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return True


def install_extension(*, dry_run: bool = False) -> tuple[Path, bool]:
    """Copy the extension to ~/.mneva/extension and return (path, changed).

    "Load unpacked" keeps pointing at whatever folder it was given. The
    package folder is wrong for that: uvx runs from a cache that gets pruned,
    and upgrades replace the files under a loaded extension. A copy in the
    data root stays put and changes only when setup refreshes it.
    """
    target = mneva_home() / "extension"
    shipped = {p.name: p for p in EXTENSION_DIR.iterdir() if p.is_file()}
    changed = False
    for name, source in sorted(shipped.items()):
        changed |= _write_if_changed(target / name, source.read_bytes(), dry_run=dry_run)
    if target.is_dir():
        for leftover in target.iterdir():
            if leftover.is_file() and leftover.name not in shipped:
                changed = True
                if not dry_run:
                    leftover.unlink()
    return target, changed


def register(launcher_argv: list[str], *, dry_run: bool = False) -> str:
    """Register the host with Chrome, Edge and Chromium for this user.

    Writes a launcher and the host manifest under ~/.mneva/native-host, then
    points each browser at the manifest. Idempotent; returns one status line.
    """
    host_dir = mneva_home() / "native-host"
    if sys.platform == "win32":
        launcher = host_dir / "mneva-native-host.bat"
        launcher_text = f"@echo off\r\n{subprocess.list2cmdline(launcher_argv)} %*\r\n"
    else:
        launcher = host_dir / "mneva-native-host"
        launcher_text = f'#!/bin/sh\nexec {shlex.join(launcher_argv)} "$@"\n'
    manifest_path = host_dir / f"{HOST_NAME}.json"
    manifest = {
        "name": HOST_NAME,
        "description": "Reads your mneva profile for the mneva browser extension",
        "path": str(launcher),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{i}/" for i in extension_ids()],
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")

    changed = _write_if_changed(launcher, launcher_text.encode("utf-8"), dry_run=dry_run)
    if not dry_run and sys.platform != "win32":
        launcher.chmod(0o755)
    changed |= _write_if_changed(manifest_path, manifest_bytes, dry_run=dry_run)

    browsers = []
    if sys.platform == "win32":
        for browser, parent in _WINDOWS_REGISTRY_PARENTS.items():
            key = f"{parent}\\{HOST_NAME}"
            if _registry_get(key) != str(manifest_path):
                changed = True
                if not dry_run:
                    _registry_set(key, str(manifest_path))
            browsers.append(browser)
    else:
        dirs = _MACOS_PROFILE_DIRS if sys.platform == "darwin" else _LINUX_PROFILE_DIRS
        for browser, rel in dirs.items():
            profile_dir = Path.home() / rel
            if not profile_dir.is_dir():  # browser not installed: leave no trace
                continue
            target = profile_dir / "NativeMessagingHosts" / f"{HOST_NAME}.json"
            changed |= _write_if_changed(target, manifest_bytes, dry_run=dry_run)
            browsers.append(browser)

    names = ", ".join(browsers) or "no supported browser found"
    if not changed:
        return f"Browser bridge: already registered ({names}), left unchanged"
    return f"Browser bridge: {'would register' if dry_run else 'registered'} for {names}"


if __name__ == "__main__":
    main()
