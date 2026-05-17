"""Obsidian vault read-write integration.

A directory qualifies as a vault only if it contains a ``.obsidian/``
subdirectory. ``detect_vault`` enforces this so ``mneva config set vault``
cannot accidentally point at ``/etc/`` or ``$HOME``.

When configured, ``mneva capture`` writes each new record into BOTH
``~/.mneva/store/<id>.md`` and ``<vault>/mneva/<scope>/<id>.md``. The
vault copy uses the same YAML frontmatter format so Obsidian sees it
as a normal note. Vault writes are best-effort: any failure logs a
warning and capture continues. Capture never fails because of a vault
problem.

``sync_from_vault`` is the round-trip half. It walks ``<vault>/mneva/``
and imports notes back into the local store. Only notes carrying an
``mneva_id`` in their frontmatter are imported: this prevents
accidentally pulling in unrelated notes the user wrote themselves.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from mneva.store import Record, write_record

_LOG = logging.getLogger("mneva.vault")


class VaultError(Exception):
    """Recoverable vault problem (capture continues; vault step is skipped)."""


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Result of ``sync_from_vault``: how many records imported vs skipped."""

    imported: int
    skipped: int


def detect_vault(path: Path) -> bool:
    """A path is a vault iff it is a directory containing ``.obsidian/``.

    This is mandatory: arbitrary directories (``/etc``, ``$HOME``,
    ``D:/``) must never be accepted as vaults. The ``.obsidian/``
    marker is created the first time Obsidian opens a directory.
    """
    return path.is_dir() and (path / ".obsidian").is_dir()


def vault_record_path(record: Record, vault: Path) -> Path:
    """Compute the canonical vault path for a record.

    Layout: ``<vault>/mneva/<scope>/<record_id>.md``. Scope is part of
    the path so users browsing Obsidian see records grouped by project.
    """
    return vault / "mneva" / record.scope / f"{record.id}.md"


def write_to_vault(record: Record, vault: Path) -> Path:
    """Write a record into the vault. Returns the path written.

    Raises ``VaultError`` if the path is not a valid vault. The caller
    decides whether to swallow the error (capture flow) or surface it
    (config set-vault flow).
    """
    if not detect_vault(vault):
        raise VaultError(
            f"not a valid Obsidian vault (no .obsidian/ subdirectory): {vault}"
        )
    target = vault_record_path(record, vault)
    target.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        record.body,
        mneva_id=record.id,
        scope=record.scope,
        lifespan=record.lifespan,
        tool=record.tool,
        source=record.source,
    )
    target.write_text(frontmatter.dumps(post), encoding="utf-8")
    return target


def sync_from_vault(vault: Path, home: Path) -> SyncResult:
    """Import vault notes carrying ``mneva_id`` back into the local store.

    Notes without ``mneva_id`` in frontmatter are skipped (they belong
    to the user, not to mneva). Existing records in the local store
    are overwritten with the vault version — the vault wins on conflict
    so the user can edit notes in Obsidian.

    Raises ``VaultError`` if the path is not a valid vault.
    """
    if not detect_vault(vault):
        raise VaultError(
            f"not a valid Obsidian vault (no .obsidian/ subdirectory): {vault}"
        )
    mneva_dir = vault / "mneva"
    if not mneva_dir.exists():
        return SyncResult(imported=0, skipped=0)

    imported = 0
    skipped = 0
    for md_path in sorted(mneva_dir.rglob("*.md")):
        try:
            post = frontmatter.loads(md_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _LOG.warning("vault: skipping unreadable note %s: %s", md_path, exc)
            skipped += 1
            continue

        if "mneva_id" not in post:
            skipped += 1
            continue

        record = Record(
            id=str(post["mneva_id"]),
            scope=str(post.get("scope", "unknown")),
            lifespan=str(post.get("lifespan", "permanent")),
            tool=str(post.get("tool", "vault")),
            body=post.content,
            source=post.get("source"),
        )
        write_record(record, home=home, overwrite=True)
        imported += 1
    return SyncResult(imported=imported, skipped=skipped)
