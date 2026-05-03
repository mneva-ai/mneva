from __future__ import annotations

import click

from mneva import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="mneva")
def app() -> None:
    """Mneva — persistent agent context substrate."""


@app.command()
def init() -> None:
    """Initialize ~/.mneva/ (data root, token, bootstrap)."""
    raise click.ClickException("not implemented yet")


@app.command()
@click.option("--scope", required=True)
@click.option("--tool", default="cli")
@click.option("--lifespan", type=click.Choice(["transient", "permanent"]), default="transient")
@click.argument("body", required=False)
def capture(scope: str, tool: str, lifespan: str, body: str | None) -> None:
    """Capture a record from a positional body or stdin."""
    raise click.ClickException("not implemented yet")


@app.command()
@click.argument("query")
@click.option("--scope", default=None)
@click.option("--lifespan", type=click.Choice(["transient", "permanent"]), default=None)
def search(query: str, scope: str | None, lifespan: str | None) -> None:
    """Search the index."""
    raise click.ClickException("not implemented yet")


@app.command()
def status() -> None:
    """Report token, indexed counts, vec/bm25 mode."""
    raise click.ClickException("not implemented yet")


@app.command()
@click.argument("record_id")
@click.option("--confirm", is_flag=True, required=True)
def forget(record_id: str, confirm: bool) -> None:
    """Delete a record by id (requires --confirm)."""
    raise click.ClickException("not implemented yet")


@app.command()
def config() -> None:
    """Stub. Real subcommands wired later."""
    raise click.ClickException("not implemented yet")


@app.command()
def serve() -> None:
    """Stub. Real impl in M4."""
    raise click.ClickException("not implemented yet")


if __name__ == "__main__":
    app()
