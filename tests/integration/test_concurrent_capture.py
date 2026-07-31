"""Concurrency + WAL regression tests for ``Indexer``.

v0.2 enables WAL mode + busy_timeout in ``Indexer.__init__`` so multiple
``mneva-mcp`` processes (one per AI client) can share the same store
without ``database is locked`` errors. These tests use threads with separate
Indexer instances against the same DB file — same lock arbitration path as
real subprocesses, faster to run, deterministic.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from mneva.indexer import Indexer
from mneva.store import Record, make_record_id, write_record

pytestmark = pytest.mark.integration


def test_indexer_enables_wal_on_init(tmp_mneva_home: Path) -> None:
    """After Indexer() opens, the SQLite file is in WAL journal mode."""
    Indexer(tmp_mneva_home / "mneva.sqlite")
    # Open a fresh connection to read the persisted PRAGMA (journal_mode
    # persists on the file once any connection sets WAL).
    probe = sqlite3.connect(tmp_mneva_home / "mneva.sqlite")
    mode = probe.execute("PRAGMA journal_mode").fetchone()[0]
    probe.close()
    assert mode.lower() == "wal"


def test_concurrent_writers_do_not_lose_records(tmp_mneva_home: Path) -> None:
    """Two Indexer instances writing in parallel both commit, none lost."""
    db_path = tmp_mneva_home / "mneva.sqlite"
    # Pre-open the DB once so WAL is enabled before the threads race.
    Indexer(db_path)

    errors: list[BaseException] = []

    def writer(worker_id: int, n: int) -> None:
        try:
            idx = Indexer(db_path)
            for i in range(n):
                body = f"worker-{worker_id} record-{i}"
                record = Record(
                    id=make_record_id(f"scope-{worker_id}", body),
                    scope=f"scope-{worker_id}",
                    lifespan="transient",
                    tool="test",
                    body=body,
                )
                write_record(record, home=tmp_mneva_home)
                idx.add(record)
        except (sqlite3.OperationalError, OSError) as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer, args=(0, 10)),
        threading.Thread(target=writer, args=(1, 10)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"writer threads raised: {errors!r}"

    final = Indexer(db_path)
    count = int(final.status()["count"])
    assert count == 20


def test_wal_upgrade_from_legacy_journal_mode(tmp_mneva_home: Path) -> None:
    """A v0.1.x DB with default DELETE journal mode upgrades cleanly to WAL.

    Locked by /plan-eng-review as the IRON regression for the v0.2 PRAGMA
    patch. v0.1.x users running ``pipx upgrade mneva`` must not lose data or
    see migration errors.
    """
    from mneva.store import Record, write_record

    db_path = tmp_mneva_home / "mneva.sqlite"

    # A v0.1.x install always wrote the Markdown file first and indexed second
    # (cli.py capture), so a real legacy record exists in BOTH places. Write the
    # Markdown too, otherwise this fixture describes a state no install can
    # reach: an index row with no backing file.
    write_record(
        Record(
            id="legacy01",
            scope="legacy-scope",
            lifespan="transient",
            tool="cli",
            body="legacy data",
        ),
        home=tmp_mneva_home,
    )

    # Simulate a v0.1.x install: open with default journal mode, add a row,
    # commit, close. Default mode is DELETE.
    legacy = sqlite3.connect(db_path)
    legacy.execute(
        "CREATE TABLE IF NOT EXISTS records ("
        "id TEXT PRIMARY KEY, scope TEXT, lifespan TEXT, tool TEXT, body TEXT)"
    )
    legacy.execute(
        "INSERT INTO records(id, scope, lifespan, tool, body) "
        "VALUES (?, ?, ?, ?, ?)",
        ("legacy01", "legacy-scope", "transient", "cli", "legacy data"),
    )
    legacy.commit()
    legacy_mode = legacy.execute("PRAGMA journal_mode").fetchone()[0]
    legacy.close()
    assert legacy_mode.lower() == "delete"

    # Open with the current Indexer. WAL kicks in; legacy record survives.
    idx = Indexer(db_path)
    assert int(idx.status()["count"]) == 1
    # Survives as a real record, not just a row count.
    assert any(h.id == "legacy01" for h in idx.search("legacy data"))

    # Verify journal_mode persisted as WAL on the file.
    probe = sqlite3.connect(db_path)
    mode = probe.execute("PRAGMA journal_mode").fetchone()[0]
    probe.close()
    assert mode.lower() == "wal"


def test_concurrent_migration_of_stale_db_leaves_a_complete_index(
    tmp_mneva_home: Path,
) -> None:
    """Two clients opening one stale DB concurrently both succeed, index complete.

    This is the realistic mneva-mcp startup race: one process per AI client,
    all pointed at the same store, all opening at once after an upgrade.

    Caught a real bug: ``PRAGMA journal_mode=WAL`` used to run *before*
    ``busy_timeout`` was set, and SQLite returns SQLITE_BUSY for a journal-mode
    conversion *without* invoking the busy handler -- so a concurrent opener
    got "database is locked" outright. The older concurrency test above hides
    this by pre-opening the DB once before racing.

    Note on scope: this does NOT reproduce an interleaved rebuild. SQLite's
    single-writer lock plus busy_timeout already serializes the two rebuilds,
    and both are full rebuilds, so the result is complete either way. The
    property BEGIN IMMEDIATE actually buys is tested by
    test_failed_rebuild_does_not_stamp_the_schema_version.
    """
    from mneva.store import Record, write_record

    db_path = tmp_mneva_home / "mneva.sqlite"
    expected = 40
    for i in range(expected):
        write_record(
            Record(
                id=f"conc{i:03d}",
                scope="s",
                lifespan="permanent",
                tool="cli",
                body=f"concurrent migration record {i}",
            ),
            home=tmp_mneva_home,
        )

    # A stale, pre-versioning database (user_version defaults to 0).
    legacy = sqlite3.connect(db_path)
    legacy.execute(
        "CREATE TABLE records ("
        "id TEXT PRIMARY KEY, scope TEXT, lifespan TEXT, tool TEXT, body TEXT)"
    )
    legacy.commit()
    legacy.close()

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def migrate() -> None:
        try:
            barrier.wait(timeout=10)
            Indexer(db_path)
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=migrate) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"migration raised: {errors}"
    on_disk = len(list((tmp_mneva_home / "store").glob("*.md")))
    assert on_disk == expected
    assert int(Indexer(db_path).status()["count"]) == expected
