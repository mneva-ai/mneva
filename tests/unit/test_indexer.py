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
