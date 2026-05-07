from __future__ import annotations

import hashlib
import sys
import time

import click

from mneva import __version__
from mneva.config import load_config
from mneva.indexer import Indexer
from mneva.paths import ensure_home
from mneva.providers import get_provider
from mneva.store import Record, forget_record, write_record
from mneva.synth import digest_to_bootstrap, synthesize_2stage


def _new_id(scope: str, body: str) -> str:
    raw = f"{scope}|{time.time_ns()}|{body[:64]}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]

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
        id=_new_id(scope, body),
        scope=scope,
        lifespan=lifespan,
        tool=tool,
        body=body,
        source=source,
    )
    write_record(record, home=home)
    Indexer(home / "mneva.sqlite").add(record)
    click.echo(record.id)


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


@app.command()
def config() -> None:
    """Stub. Real subcommands wired later."""
    raise click.ClickException("not implemented yet")


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
    if not (home / "config.json").exists():
        raise click.ClickException("run `mneva init` first")
    if _port_in_use(port):
        raise click.ClickException(
            f"port {port} is already in use -- choose a different --port or stop the other process"
        )
    import uvicorn

    from mneva.api import create_app
    from mneva.config import load_config

    config = load_config(home)
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
    if not (home / "config.json").exists():
        raise click.ClickException("run `mneva init` first")
    cfg = load_config(home)
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
    except ValueError as e:
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
    if not (home / "config.json").exists():
        raise click.ClickException("run `mneva init` first")
    cfg = load_config(home)
    chosen = backend or cfg.synthesize_default_backend
    try:
        provider = get_provider(chosen)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    try:
        text = digest_to_bootstrap(provider, scope=scope, home=home)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    if write_bootstrap:
        target = home / "bootstrap.md"
        target.write_text(text, encoding="utf-8")
        click.echo(f"wrote {target}")
    else:
        click.echo(text)


if __name__ == "__main__":
    app()
