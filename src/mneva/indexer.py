from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from mneva.paths import mneva_home
from mneva.store import Record, read_record


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
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._has_vec = try_load_sqlite_vec(self._conn)
        self._init_schema()

    def _init_schema(self) -> None:
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
        self._conn.commit()

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
        home = mneva_home()
        return [read_record(row["id"], home=home) for row, _ in ranked[:k]]

    def status(self) -> dict[str, int | str]:
        count = self._conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        return {"mode": self.mode, "count": int(count)}
