from __future__ import annotations

from pathlib import Path

import pytest

from mneva.paths import ensure_home
from mneva.store import Record, read_record, write_record


def test_write_then_read_roundtrip(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    rec = Record(
        id="abc123",
        scope="ticket-42",
        lifespan="permanent",
        tool="claude-code",
        body="The decision was X because Y.",
        source="session://2026-05-02/abc",
    )
    written = write_record(rec, home=home)
    assert written.exists()
    assert written.parent == home / "store"

    loaded = read_record("abc123", home=home)
    assert loaded == rec


def test_write_rejects_duplicate_without_overwrite(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    rec = Record(id="dup", scope="s", lifespan="transient", tool="cursor", body="hi")
    write_record(rec, home=home)
    with pytest.raises(FileExistsError):
        write_record(rec, home=home)


def test_write_overwrite_true_replaces(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    a = Record(id="x", scope="s", lifespan="transient", tool="cursor", body="A")
    b = Record(id="x", scope="s", lifespan="transient", tool="cursor", body="B")
    write_record(a, home=home)
    write_record(b, home=home, overwrite=True)
    assert read_record("x", home=home).body == "B"
