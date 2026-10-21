from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
EXTENSION = REPO / "src" / "mneva" / "extension"


def _build_module() -> ModuleType:
    # store/ is a repo tool, not part of the package.
    spec = importlib.util.spec_from_file_location("store_build", REPO / "store" / "build.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_store_zip_drops_key_and_keeps_everything_else(tmp_path: Path) -> None:
    out = _build_module().build(EXTENSION, tmp_path / "ext.zip")

    source_manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    assert "key" in source_manifest, "the dev copy keeps its key for a stable ID"
    with zipfile.ZipFile(out) as z:
        names = sorted(z.namelist())
        manifest = json.loads(z.read("manifest.json"))
        others = {n: z.read(n) for n in names if n != "manifest.json"}

    # The stores reject `key`; every other field must match the dev copy.
    assert "key" not in manifest
    assert manifest == {k: v for k, v in source_manifest.items() if k != "key"}
    assert names == sorted(p.relative_to(EXTENSION).as_posix()
                           for p in EXTENSION.rglob("*") if p.is_file())
    for name, data in others.items():
        assert data == (EXTENSION / name).read_bytes(), name
