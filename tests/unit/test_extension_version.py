"""The browser extension reloads itself only when its manifest version changes.

Chrome keeps running the files it loaded until the extension reloads, and the
extension decides to reload by comparing manifest versions. A change to any
extension file without a version bump would therefore never reach users.
"""
from __future__ import annotations

import hashlib
import json

from mneva.native_host import EXTENSION_DIR

VERSION = "0.3.0"
FILES_SHA256 = "dce6049bd1046e3b5dcafc44c60846c1cc48e9426a7e5a76e506c8b401065d8f"


def _files_sha256() -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in EXTENSION_DIR.iterdir() if p.is_file()):
        digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def test_extension_changes_come_with_a_version_bump() -> None:
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert (manifest["version"], _files_sha256()) == (VERSION, FILES_SHA256), (
        "Extension files changed. Bump the version in extension/manifest.json, "
        "then set VERSION and FILES_SHA256 in this test to the new values."
    )


def test_host_permissions_cover_exactly_the_content_script_sites() -> None:
    # Needed to put the content script back into open tabs after a reload;
    # any wider and Chrome asks the user for more than the extension uses.
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))
    sites = [m for script in manifest["content_scripts"] for m in script["matches"]]
    assert manifest["host_permissions"] == sites
