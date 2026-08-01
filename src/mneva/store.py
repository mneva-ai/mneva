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
    # Git provenance. `repo` is the filter key and survives a clone; the rest
    # are context. All optional: records captured outside a repo, and every
    # record written before v0.3, simply have none.
    repo: str | None = None
    repo_path: str | None = None
    branch: str | None = None
    commit_sha: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Single-source serialization for MCP tools (and any future caller)."""
        return {
            "id": self.id,
            "scope": self.scope,
            "lifespan": self.lifespan,
            "tool": self.tool,
            "body": self.body,
            "source": self.source,
            "repo": self.repo,
            "repo_path": self.repo_path,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
        }


# Optional fields that are omitted from frontmatter entirely when unset,
# rather than written as `null`. Four `null` lines at the top of every note
# would undermine the Obsidian readability this project sells.
_OPTIONAL_FRONTMATTER_FIELDS = ("repo", "repo_path", "branch", "commit_sha")


def record_frontmatter(record: Record, **extra: Any) -> dict[str, Any]:
    """Build the YAML frontmatter mapping for a record.

    Single source of truth for what a record looks like on disk. `store` and
    `vault` both go through this: they used to keep separate hardcoded field
    lists, so every new field had to be added in three places and any miss
    silently dropped data on the vault round trip.
    """
    data: dict[str, Any] = {
        "scope": record.scope,
        "lifespan": record.lifespan,
        "tool": record.tool,
        "source": record.source,
    }
    for name in _OPTIONAL_FRONTMATTER_FIELDS:
        value = getattr(record, name)
        if value is not None:
            data[name] = value
    data.update(extra)
    return data


def record_from_frontmatter(post: frontmatter.Post, *, record_id: str) -> Record:
    """Rebuild a Record from parsed frontmatter. Inverse of `record_frontmatter`.

    Tolerates missing keys throughout: pre-v0.3 files have no git fields, and
    a hand-edited Obsidian note may be missing anything.
    """

    def opt(key: str) -> str | None:
        raw = post.get(key)
        return str(raw) if raw is not None else None

    return Record(
        id=record_id,
        scope=str(post.get("scope", "unknown")),
        lifespan=str(post.get("lifespan", "permanent")),
        tool=str(post.get("tool", "unknown")),
        body=post.content,
        source=opt("source"),
        repo=opt("repo"),
        repo_path=opt("repo_path"),
        branch=opt("branch"),
        commit_sha=opt("commit_sha"),
    )


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
    post = frontmatter.Post(record.body, **record_frontmatter(record))
    target.write_text(frontmatter.dumps(post), encoding="utf-8")
    return target


def read_record(record_id: str, *, home: Path) -> Record:
    target = _path_for(record_id, home=home)
    post = frontmatter.loads(target.read_text(encoding="utf-8"))
    return record_from_frontmatter(post, record_id=record_id)


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
