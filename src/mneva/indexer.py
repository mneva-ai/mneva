from __future__ import annotations

import contextlib
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
_SCHEMA_VERSION = 2

# Every INSERT into `records` goes through these two constants. They were
# duplicated across add() and rebuild(), which meant a new column could land in
# one path and not the other -- and since rebuild() runs on `mneva reindex`,
# that silently blanks the column for the whole index.
_INSERT_SQL = (
    "INSERT OR REPLACE INTO records(id, scope, lifespan, tool, body, repo) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)


def _insert_params(record: Record) -> tuple[Any, ...]:
    return (
        record.id,
        record.scope,
        record.lifespan,
        record.tool,
        record.body,
        record.repo,
    )


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
        # busy_timeout first: every statement below (and the migration in
        # _init_schema) should wait for a competing writer rather than raise.
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._enable_wal()
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.row_factory = sqlite3.Row
        self._has_vec = try_load_sqlite_vec(self._conn)
        self._init_schema()

    def _enable_wal(self) -> None:
        """Best-effort switch to WAL.

        Converting `journal_mode` needs a lock that SQLite will not wait for:
        it returns SQLITE_BUSY immediately *without* invoking the busy handler,
        so `busy_timeout` cannot help here. Two clients opening a fresh or
        pre-WAL database at the same moment therefore race, and one loses.

        Losing is harmless. The winner is setting WAL on the same file, and the
        mode persists on disk once any connection sets it. Raising here would
        turn a benign race into a failed `mneva-mcp` startup.
        """
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("PRAGMA journal_mode=WAL")

    def _create_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id        TEXT PRIMARY KEY,
                scope     TEXT NOT NULL,
                lifespan  TEXT NOT NULL,
                tool      TEXT NOT NULL,
                body      TEXT NOT NULL,
                repo      TEXT
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
        self.rebuild(only_if_stale=True)

    def _count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM records").fetchone()[0])

    def rebuild(self, *, only_if_stale: bool = False) -> int:
        """Drop the index and repopulate it from the Markdown store.

        Returns the number of records indexed. Safe to call at any time — the
        index holds no data that does not also live in `~/.mneva/store/*.md`.

        Runs under `BEGIN IMMEDIATE` so the DROP, the inserts, and the version
        stamp commit as one unit. Without it the DDL autocommits on its own, so
        a failure part-way through leaves an emptied table behind; if the stamp
        had also landed, every later open would skip the rebuild and the index
        would stay silently incomplete forever. That is the failure mode schema
        versioning exists to prevent, so the rebuild must not be able to cause
        it. Covered by test_failed_rebuild_does_not_stamp_the_schema_version.

        With `only_if_stale`, the version is re-checked *after* the lock is
        held, so a process that was waiting on a concurrent migration becomes a
        no-op instead of dropping the winner's freshly built table.

        (Note: SQLite's single-writer lock plus `busy_timeout` already prevents
        two concurrent rebuilds from interleaving their rows, and both would be
        full rebuilds anyway. The lock here is about atomicity, not that race.)
        """
        if self._conn.in_transaction:
            self._conn.commit()
        # busy_timeout (set in __init__) makes a competing writer wait here
        # rather than raise "database is locked".
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            if only_if_stale:
                current = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
                if current == _SCHEMA_VERSION:
                    # Another process migrated while we waited for the lock.
                    self._conn.rollback()
                    return self._count()
            self._conn.execute("DROP TABLE IF EXISTS records")
            self._create_table()
            count = 0
            for record in iter_records(home=self._home):
                self._conn.execute(_INSERT_SQL, _insert_params(record))
                count += 1
            # PRAGMA user_version does not accept a bound parameter. It lives in
            # the database header and is transactional, so it commits with the
            # rows above — never a version stamp without the data behind it.
            self._conn.execute(f"PRAGMA user_version = {int(_SCHEMA_VERSION)}")
        except BaseException:
            self._conn.rollback()
            raise
        self._conn.commit()
        return count

    def close(self) -> None:
        """Close the sqlite connection.

        Windows keeps a file locked until every handle is closed, and relying
        on refcounting to do it is not safe: under coverage (which CI runs) the
        tracer holds frame references alive, so connections outlive the scope
        that created them and the database file cannot be deleted or replaced.
        """
        self._conn.close()

    def __enter__(self) -> Indexer:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def mode(self) -> str:
        return "sqlite-vec" if self._has_vec else "bm25"

    def add(self, record: Record) -> None:
        self._conn.execute(_INSERT_SQL, _insert_params(record))
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
        repo: str | None = None,
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
        if repo is not None:
            # `OR repo IS NULL` is load-bearing, not defensive. Every record
            # written before v0.3 has repo = NULL, and so does anything captured
            # outside a git repo. A bare `repo = ?` would make all of them
            # vanish from default search the moment a user upgrades. Only
            # records that explicitly belong to a *different* repo are excluded.
            clauses.append("(repo = ? OR repo IS NULL)")
            params.append(repo)
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
        # Provenance coverage is the only signal that git-aware capture is
        # actually working. The MCP path depends on the AI client passing
        # repo_path; if it does not, records land with repo = NULL and the
        # feature is inert with nothing else to indicate it.
        with_repo = self._conn.execute(
            "SELECT COUNT(*) FROM records WHERE repo IS NOT NULL"
        ).fetchone()[0]
        return {
            "mode": self.mode,
            "count": int(count),
            "with_repo": int(with_repo),
        }
