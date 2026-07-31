from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from mneva.store import Record, iter_records, read_record

# Bump whenever the `records` table shape changes. On open, a database at a
# lower version is dropped and rebuilt from the Markdown store, which is the
# source of truth. Without this, `CREATE TABLE IF NOT EXISTS` silently keeps
# the old shape and every new column is missing forever.
_SCHEMA_VERSION = 1


def try_load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Attempt to load the sqlite-vec extension. Return True iff it loaded."""
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False


_TOKEN = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


class Indexer:
    """Hybrid index. v0 ships BM25 backbone; sqlite-vec re-ranks when available."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._home = db_path.parent
        # WAL + busy_timeout enable concurrent mneva-mcp processes (one per AI
        # client) to share the same store without `database is locked` errors.
        # WAL persists on the file once any connection enables it, so existing
        # v0.1.x databases auto-upgrade on first v0.2 open with no migration.
        self._conn = sqlite3.connect(db_path, timeout=5.0)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.row_factory = sqlite3.Row
        self._has_vec = try_load_sqlite_vec(self._conn)
        self._init_schema()

    def _create_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id        TEXT PRIMARY KEY,
                scope     TEXT NOT NULL,
                lifespan  TEXT NOT NULL,
                tool      TEXT NOT NULL,
                body      TEXT NOT NULL
            )
            """
        )

    def _init_schema(self) -> None:
        found = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        if found == _SCHEMA_VERSION:
            self._create_table()
            self._conn.commit()
            return
        # Stale (or pre-versioning, i.e. 0) schema. The Markdown store is the
        # source of truth, so drop and repopulate rather than trying to patch
        # columns onto whatever shape happens to be on disk.
        self.rebuild()

    def rebuild(self) -> int:
        """Drop the index and repopulate it from the Markdown store.

        Returns the number of records indexed. Safe to call at any time — the
        index holds no data that does not also live in `~/.mneva/store/*.md`.
        """
        self._conn.execute("DROP TABLE IF EXISTS records")
        self._create_table()
        count = 0
        for record in iter_records(home=self._home):
            self._conn.execute(
                "INSERT OR REPLACE INTO records(id, scope, lifespan, tool, body) "
                "VALUES (?, ?, ?, ?, ?)",
                (record.id, record.scope, record.lifespan, record.tool, record.body),
            )
            count += 1
        # PRAGMA user_version does not accept a bound parameter.
        self._conn.execute(f"PRAGMA user_version = {int(_SCHEMA_VERSION)}")
        self._conn.commit()
        return count

    @property
    def mode(self) -> str:
        return "sqlite-vec" if self._has_vec else "bm25"

    def add(self, record: Record) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO records(id, scope, lifespan, tool, body) "
            "VALUES (?, ?, ?, ?, ?)",
            (record.id, record.scope, record.lifespan, record.tool, record.body),
        )
        self._conn.commit()

    def remove(self, record_id: str) -> None:
        self._conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        self._conn.commit()

    def search(
        self,
        query: str,
        *,
        scope: str | None = None,
        lifespan: str | None = None,
        k: int = 10,
    ) -> list[Record]:
        clauses: list[str] = []
        params: list[Any] = []
        if scope is not None:
            clauses.append("scope = ?")
            params.append(scope)
        if lifespan is not None:
            clauses.append("lifespan = ?")
            params.append(lifespan)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT id, body FROM records{where}", params  # noqa: S608
        ).fetchall()
        if not rows:
            return []
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return []
        # BM25 IDF can be negative on tiny corpora, so filter on actual token
        # overlap first; BM25 just ranks the candidates.
        candidates = [r for r in rows if query_tokens & set(_tokenize(r["body"]))]
        if not candidates:
            return []
        corpus = [_tokenize(r["body"]) for r in candidates]
        bm = BM25Okapi(corpus)
        scores = bm.get_scores(list(query_tokens))
        ranked = sorted(zip(candidates, scores, strict=False), key=lambda x: x[1], reverse=True)
        return [read_record(row["id"], home=self._home) for row, _ in ranked[:k]]

    def status(self) -> dict[str, int | str]:
        count = self._conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        return {"mode": self.mode, "count": int(count)}
