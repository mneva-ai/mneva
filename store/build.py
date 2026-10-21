"""Build the extension zip to upload to the Chrome Web Store and Edge Add-ons.

    python store/build.py            -> dist/mneva-extension-<version>.zip

The dev copy's manifest carries `key` so an unpacked install keeps the ID the
native host allows. Both stores reject `key` and assign their own ID, so the
upload drops it; every other file goes in unchanged.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXTENSION = REPO / "src" / "mneva" / "extension"


def build(source: Path, out: Path) -> Path:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("key", None)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            name = path.relative_to(source).as_posix()
            if name == "manifest.json":
                z.writestr(name, json.dumps(manifest, indent=2) + "\n")
            else:
                z.write(path, name)
    return out


def main() -> None:
    version = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))["version"]
    out = build(EXTENSION, REPO / "dist" / f"mneva-extension-{version}.zip")
    print(out)


if __name__ == "__main__":
    sys.exit(main())
