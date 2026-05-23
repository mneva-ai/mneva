from __future__ import annotations

import hashlib
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter


@dataclass(frozen=True, slots=True)
class Record:
    id: str
    scope: str
    lifespan: str
    tool: str
    body: str
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Single-source serialization for MCP tools (and any future caller)."""
        return {
            "id": self.id,
            "scope": self.scope,
            "lifespan": self.lifespan,
            "tool": self.tool,
            "body": self.body,
            "source": self.source,
        }


def make_record_id(scope: str, body: str) -> str:
    """Generate a 16-hex-char record id from scope, time, and body prefix.

    Time-based component makes practical collisions impossible.
    """
    raw = f"{scope}|{time.time_ns()}|{body[:64]}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _path_for(record_id: str, *, home: Path) -> Path:
    return home / "store" / f"{record_id}.md"


def write_record(record: Record, *, home: Path, overwrite: bool = False) -> Path:
    target = _path_for(record.id, home=home)
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        record.body,
        scope=record.scope,
        lifespan=record.lifespan,
        tool=record.tool,
        source=record.source,
    )
    target.write_text(frontmatter.dumps(post), encoding="utf-8")
    return target


def read_record(record_id: str, *, home: Path) -> Record:
    target = _path_for(record_id, home=home)
    post = frontmatter.loads(target.read_text(encoding="utf-8"))
    raw_source = post.get("source")
    return Record(
        id=record_id,
        scope=str(post["scope"]),
        lifespan=str(post["lifespan"]),
        tool=str(post["tool"]),
        body=post.content,
        source=str(raw_source) if raw_source is not None else None,
    )


def forget_record(record_id: str, *, home: Path) -> bool:
    target = _path_for(record_id, home=home)
    if not target.exists():
        return False
    target.unlink()
    return True


def iter_records(*, home: Path) -> Iterator[Record]:
    store = home / "store"
    if not store.exists():
        return
    for path in sorted(store.glob("*.md")):
        yield read_record(path.stem, home=home)
