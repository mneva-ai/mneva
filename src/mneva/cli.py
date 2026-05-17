from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import click

from mneva import __version__
from mneva.config import ConfigError, load_config, save_config
from mneva.indexer import Indexer
from mneva.paths import ensure_home
from mneva.providers import ProviderError, get_provider
from mneva.store import Record, forget_record, make_record_id, write_record
from mneva.synth import digest_to_bootstrap, synthesize_2stage

# Force UTF-8 stdout on Windows; default cp1252 crashes on LLM Unicode output.
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


BOOTSTRAP_TEMPLATE = """\
# Mneva Bootstrap

Keep this file under 350 lines. It is the L1 entrance — rules + scope index, not content.

## Active scopes
-

## Rules
- Append-mode by default. Edit-mode requires --edit.
- One concern per file. No god files.
- transient context is not searched outside the active scope.

## Recent decisions
-
"""


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="mneva")
def app() -> None:
    """Mneva — persistent agent context substrate."""


@app.command()
def init() -> None:
    """Initialize ~/.mneva/ (data root, token, bootstrap). Idempotent on token."""
    from mneva.config import Config, generate_token, load_config, save_config
    from mneva.paths import ensure_home

    home = ensure_home()
    config_path = home / "config.json"
    if config_path.exists():
        cfg = load_config(home)
    else:
        cfg = Config(token=generate_token())
        save_config(cfg, home)

    bootstrap = home / "bootstrap.md"
    if not bootstrap.exists():
        bootstrap.write_text(BOOTSTRAP_TEMPLATE, encoding="utf-8")

    click.echo(f"Mneva initialized at {home}")
    click.echo(f"Token (save this — shown only on init): {cfg.token}")


@app.command()
@click.option("--scope", required=True)
@click.option("--tool", default="cli")
@click.option("--lifespan", type=click.Choice(["transient", "permanent"]), default="transient")
@click.option("--source", default=None, help="Optional source URL/ref.")
@click.argument("body", required=False)
def capture(
    scope: str,
    tool: str,
    lifespan: str,
    source: str | None,
    body: str | None,
) -> None:
    """Capture a record. BODY may be a positional string or '-' for stdin."""
    if body == "-":
        body = sys.stdin.read()
    elif body is None:
        raise click.ClickException(
            "body required: pass as positional argument or '-' for stdin"
        )
    if not body.strip():
        raise click.ClickException("body is empty")
    home = ensure_home()
    record = Record(
        id=make_record_id(scope, body),
        scope=scope,
        lifespan=lifespan,
        tool=tool,
        body=body,
        source=source,
    )
    try:
        write_record(record, home=home)
    except FileExistsError as e:
        raise click.ClickException(
            f"record id collision (very rare). Retry the command. ({e})"
        ) from e
    Indexer(home / "mneva.sqlite").add(record)
    _mirror_to_vault_if_configured(record, home)
    click.echo(record.id)


def _mirror_to_vault_if_configured(record: Record, home: Path) -> None:
    """Best-effort vault mirror for `capture`. Never raises.

    If the user has not run `mneva init` or has not set a vault, this is
    a no-op. If the vault is configured but the write fails (missing
    `.obsidian/`, permissions, iCloud lock), we print a warning to stderr
    and continue. Capture must never fail because of vault.
    """
    if not (home / "config.json").exists():
        return
    try:
        cfg = load_config(home)
    except ConfigError:
        return
    if not cfg.vault_path:
        return
    from mneva.vault import VaultError, write_to_vault

    try:
        target = write_to_vault(record, Path(cfg.vault_path))
        click.echo(f"  -> vault: {target}", err=True)
    except (VaultError, OSError) as exc:
        click.echo(f"  warning: vault write failed: {exc}", err=True)


@app.command()
@click.argument("query")
@click.option("--scope", default=None)
@click.option("--lifespan", type=click.Choice(["transient", "permanent"]), default=None)
@click.option("-k", "top_k", default=10, type=int)
def search(query: str, scope: str | None, lifespan: str | None, top_k: int) -> None:
    """Search the index. Scope filter narrows; lifespan filter is exact-match."""
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    hits = idx.search(query, scope=scope, lifespan=lifespan, k=top_k)
    if not hits:
        click.echo("(no matches)")
        return
    for r in hits:
        click.echo(f"--- {r.id} (scope: {r.scope}, lifespan: {r.lifespan}, tool: {r.tool}) ---")
        click.echo(r.body)


@app.command()
def status() -> None:
    """Report indexed count and active mode (sqlite-vec or bm25)."""
    home = ensure_home()
    idx = Indexer(home / "mneva.sqlite")
    s = idx.status()
    click.echo(f"home: {home}")
    click.echo(f"mode: {s['mode']}")
    click.echo(f"count: {s['count']}")


@app.command()
@click.argument("record_id")
@click.option("--confirm", is_flag=True, required=True, help="Required for safety.")
def forget(record_id: str, confirm: bool) -> None:
    """Delete a record by id. --confirm required."""
    home = ensure_home()
    existed = forget_record(record_id, home=home)
    Indexer(home / "mneva.sqlite").remove(record_id)
    if not existed:
        raise click.ClickException(f"no such record: {record_id}")
    click.echo(f"forgot: {record_id}")


@app.group()
def config() -> None:
    """Configure mneva settings (vault path, defaults, ...)."""


@config.command("set-vault")
@click.argument(
    "vault_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
def config_set_vault(vault_path: Path) -> None:
    """Set the Obsidian vault path. mneva will mirror captures to this vault."""
    from mneva.vault import detect_vault

    home = ensure_home()
    try:
        cfg = load_config(home)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    resolved = vault_path.expanduser().resolve()
    if not detect_vault(resolved):
        raise click.ClickException(
            f"{resolved} is not an Obsidian vault (missing .obsidian/ directory)"
        )
    save_config(replace(cfg, vault_path=str(resolved)), home)
    click.echo(f"vault set: {resolved}")


@config.command("get-vault")
def config_get_vault() -> None:
    """Print the configured Obsidian vault path."""
    home = ensure_home()
    try:
        cfg = load_config(home)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    if cfg.vault_path:
        click.echo(cfg.vault_path)
    else:
        click.echo("(no vault configured; run `mneva config set-vault <path>`)")


@config.command("unset-vault")
def config_unset_vault() -> None:
    """Clear the configured vault path (captures stop mirroring)."""
    home = ensure_home()
    try:
        cfg = load_config(home)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    save_config(replace(cfg, vault_path=None), home)
    click.echo("vault unset")


@app.command("sync-vault")
def sync_vault_cmd() -> None:
    """Import notes from the configured vault back into the local store.

    Only notes with `mneva_id` in their frontmatter are imported, so your
    hand-written Obsidian notes are never touched.
    """
    from mneva.vault import VaultError, sync_from_vault

    home = ensure_home()
    try:
        cfg = load_config(home)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    if not cfg.vault_path:
        raise click.ClickException(
            "no vault configured; run `mneva config set-vault <path>` first"
        )
    try:
        result = sync_from_vault(Path(cfg.vault_path), home)
    except VaultError as e:
        raise click.ClickException(str(e)) from e
    # Re-index everything we just imported
    from mneva.store import iter_records

    idx = Indexer(home / "mneva.sqlite")
    for record in iter_records(home=home):
        idx.add(record)
    click.echo(f"imported: {result.imported}, skipped: {result.skipped}")


@app.command()
@click.option(
    "--tool",
    required=True,
    type=click.Choice(["claude-code", "cursor", "codex"]),
    help="Target tool identifier.",
)
@click.option("--scope", default=None, help="Scope filter (default: all permanent records).")
def replay(tool: str, scope: str | None) -> None:
    """Print the context replay block for the given tool and optional scope."""
    from mneva.replay import render_replay

    result = render_replay(tool=tool, scope=scope)
    click.echo(result)


def _port_in_use(port: int) -> bool:
    import socket as _socket

    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@app.command()
@click.option("--port", default=7432, type=int)
@click.option("--host", default="127.0.0.1")
def serve(port: int, host: str) -> None:
    """Start the localhost API."""
    home = ensure_home()
    try:
        config = load_config(home)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    if _port_in_use(port):
        raise click.ClickException(
            f"port {port} is already in use -- choose a different --port or stop the other process"
        )
    import uvicorn

    from mneva.api import create_app

    uvicorn.run(create_app(home=home, config=config), host=host, port=port, log_level="info")


@app.command()
@click.option("--scope", required=True, help="record scope to synthesize over")
@click.option(
    "--backend",
    default=None,
    help="anthropic | openai | google | openrouter (defaults to config.synthesize_default_backend)",
)
def synthesize(scope: str, backend: str | None) -> None:
    """Two-stage synthesize: dump -> 100 ideas -> user-cut -> critical pass."""
    home = ensure_home()
    try:
        cfg = load_config(home)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    chosen = backend or cfg.synthesize_default_backend
    try:
        provider = get_provider(chosen)
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    def shortlist_input(stage1_output: str) -> str:
        click.echo("\n--- paste shortlist (one item per line, end with '.' on its own line) ---")
        lines: list[str] = []
        while True:
            line = click.get_text_stream("stdin").readline()
            if not line or line.strip() == ".":
                break
            lines.append(line.rstrip("\n"))
        return "\n".join(lines)

    try:
        synthesize_2stage(
            provider,
            scope=scope,
            home=home,
            shortlist_input=shortlist_input,
            output=click.echo,
        )
    except (ValueError, ProviderError) as e:
        raise click.ClickException(str(e)) from e


@app.command()
@click.option("--scope", default=None, help="restrict digest to one scope (default: all)")
@click.option(
    "--backend",
    default=None,
    help="anthropic | openai | google | openrouter (defaults to config.synthesize_default_backend)",
)
@click.option(
    "--write-bootstrap",
    is_flag=True,
    default=False,
    help="write the digest to ~/.mneva/bootstrap.md instead of stdout",
)
def digest(scope: str | None, backend: str | None, write_bootstrap: bool) -> None:
    """Manual L1 bootstrap consolidation (auto-trigger deferred to v0.1)."""
    home = ensure_home()
    try:
        cfg = load_config(home)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    chosen = backend or cfg.synthesize_default_backend
    try:
        provider = get_provider(chosen)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    try:
        text = digest_to_bootstrap(provider, scope=scope, home=home)
    except (ValueError, ProviderError) as e:
        raise click.ClickException(str(e)) from e
    if write_bootstrap:
        target = home / "bootstrap.md"
        target.write_text(text, encoding="utf-8")
        click.echo(f"wrote {target}")
    else:
        click.echo(text)


if __name__ == "__main__":
    app()
