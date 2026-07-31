from __future__ import annotations

from pathlib import Path

import pytest

from mneva.indexer import Indexer
from mneva.paths import ensure_home
from mneva.store import Record, write_record


def _record(rid: str, body: str, *, scope: str = "s", lifespan: str = "permanent") -> Record:
    return Record(id=rid, scope=scope, lifespan=lifespan, tool="claude-code", body=body)


def test_indexer_starts_in_a_known_mode(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    assert idx.mode in {"sqlite-vec", "bm25"}


def test_add_then_search_returns_record(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    rec = _record("r1", "the quick brown fox jumps over the lazy dog")
    write_record(rec, home=home)
    idx.add(rec)
    hits = idx.search("brown fox")
    assert any(h.id == "r1" for h in hits)


def test_scope_filter_excludes_other_scopes(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    a = _record("a", "alpha", scope="ticket-1")
    b = _record("b", "alpha", scope="ticket-2")
    for r in (a, b):
        write_record(r, home=home)
        idx.add(r)
    hits = idx.search("alpha", scope="ticket-1")
    assert {h.id for h in hits} == {"a"}


def test_lifespan_filter_excludes_transient_when_permanent_requested(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    p = _record("p", "shared", lifespan="permanent")
    t = _record("t", "shared", lifespan="transient")
    for r in (p, t):
        write_record(r, home=home)
        idx.add(r)
    hits = idx.search("shared", lifespan="permanent")
    assert {h.id for h in hits} == {"p"}


def test_remove_drops_from_index(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    rec = _record("r1", "needle in haystack")
    write_record(rec, home=home)
    idx.add(rec)
    idx.remove("r1")
    assert idx.search("needle") == []


def test_status_reports_mode_and_count(tmp_mneva_home: Path) -> None:
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    idx.add(_record("r1", "one"))
    idx.add(_record("r2", "two"))
    s = idx.status()
    assert s["mode"] in {"sqlite-vec", "bm25"}
    assert s["count"] == 2


def test_force_bm25_when_sqlite_vec_disabled(
    tmp_mneva_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mneva import indexer as idx_mod

    monkeypatch.setattr(idx_mod, "try_load_sqlite_vec", lambda _conn: False)
    home = ensure_home()
    idx = idx_mod.Indexer(home / "mneva.sqlite")
    assert idx.mode == "bm25"
    rec = _record("r1", "the quick brown fox")
    idx.add(rec)
    write_record(rec, home=home)
    assert {r.id for r in idx.search("fox")} == {"r1"}


def test_rebuild_repopulates_from_markdown(tmp_mneva_home: Path) -> None:
    """The Markdown store is the source of truth; the index is disposable."""
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    for i in range(3):
        rec = _record(f"rb{i}", f"rebuildable record number {i}")
        write_record(rec, home=home)
        idx.add(rec)
    assert idx.status()["count"] == 3

    # Wipe the index without touching the Markdown files.
    idx._conn.execute("DELETE FROM records")
    idx._conn.commit()
    assert idx.status()["count"] == 0

    assert idx.rebuild() == 3
    assert idx.status()["count"] == 3
    assert any(h.id == "rb1" for h in idx.search("rebuildable"))


def test_stale_schema_is_rebuilt_not_silently_kept(tmp_mneva_home: Path) -> None:
    """A pre-versioning DB must be rebuilt on open, not left with the old shape.

    Regression guard: `_init_schema` used to be CREATE TABLE IF NOT EXISTS with
    no version check, so any new column was a silent no-op on existing
    databases.
    """
    import sqlite3

    home = ensure_home()
    db = home / "mneva.sqlite"

    # Two records exist as Markdown; only one made it into a legacy-shaped DB.
    for i in range(2):
        write_record(_record(f"lg{i}", f"legacy record {i}"), home=home)

    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE records (id TEXT PRIMARY KEY, scope TEXT NOT NULL, "
        "lifespan TEXT NOT NULL, tool TEXT NOT NULL, body TEXT NOT NULL)"
    )
    conn.execute(
        "INSERT INTO records VALUES (?, ?, ?, ?, ?)",
        ("lg0", "s", "permanent", "claude-code", "legacy record 0"),
    )
    conn.execute("PRAGMA user_version = 0")
    conn.commit()
    conn.close()

    # Opening it must notice the stale version and rebuild from Markdown.
    idx = Indexer(db)
    assert idx.status()["count"] == 2
    assert int(idx._conn.execute("PRAGMA user_version").fetchone()[0]) > 0


def test_current_schema_version_is_not_rebuilt_every_open(tmp_mneva_home: Path) -> None:
    """An up-to-date DB keeps rows that are not on disk, proving no rebuild ran."""
    home = ensure_home()
    db = home / "mneva.sqlite"
    idx = Indexer(db)
    rec = _record("keep1", "record present in index only")
    idx.add(rec)  # deliberately NOT written to Markdown
    assert idx.status()["count"] == 1

    reopened = Indexer(db)
    assert reopened.status()["count"] == 1


def test_failed_rebuild_does_not_stamp_the_schema_version(
    tmp_mneva_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rebuild that dies part-way must not leave a stamped, partial index.

    This is what BEGIN IMMEDIATE + rollback buys. Without the transaction the
    DROP and CREATE autocommit on their own, so a failure mid-insert leaves an
    emptied table behind. If the version had also been stamped, every later
    open would skip the rebuild and the index would stay silently incomplete
    forever -- the exact failure mode schema versioning exists to prevent.
    """
    import mneva.indexer as indexer_mod

    home = ensure_home()
    for i in range(5):
        write_record(_record(f"boom{i}", f"record {i}"), home=home)

    idx = Indexer(home / "mneva.sqlite")
    assert idx.status()["count"] == 5

    def exploding_iter(*, home: Path):  # type: ignore[no-untyped-def]
        yield _record("boom0", "record 0")
        raise OSError("disk gave up mid-rebuild")

    monkeypatch.setattr(indexer_mod, "iter_records", exploding_iter)
    monkeypatch.setattr(indexer_mod, "_SCHEMA_VERSION", 99)

    with pytest.raises(OSError):
        idx.rebuild()

    # Version must still be the pre-failure value, so the next open retries.
    assert int(idx._conn.execute("PRAGMA user_version").fetchone()[0]) != 99
    # And the partial write must be gone, not half-applied.
    assert idx.status()["count"] == 5
