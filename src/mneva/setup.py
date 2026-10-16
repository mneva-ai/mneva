"""setup.py — the one command to run after `pip install mneva`.

Registers mneva's MCP server with every agent CLI it finds (Claude Code,
Codex) and writes a profile template. Each client is registered through its
own `mcp add` command rather than by editing its config file, so mneva never
has to track those file formats.

Safe to re-run: a client that already has an `mneva` server is left alone,
and an existing template is never overwritten.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import click

from mneva.paths import ensure_home, mneva_home
from mneva.upgrade import UVX, detect_install_method

SERVER_NAME = "mneva"
PROFILE_TEMPLATE_NAME = "profile-template.md"
_CLI_TIMEOUT_SECONDS = 60

PROFILE_TEMPLATE = """\
## Who I am
Role, field, the languages you want answers in.

## What I'm working on
Current projects, one line each.

## Tools I use
Which AI tools you use, and what you use each one for.

## How I want AI to work with me
Tone, how much to explain, what it should never do.

## Style for video and image tools
Look, pacing, references, brand rules.

## Current priorities
What matters this month.
"""


@dataclass(frozen=True)
class AgentClient:
    label: str
    exe: str
    # Value of MNEVA_MCP_CLIENT, so memories record which agent wrote them.
    client_id: str
    # Arguments between the executable and the server name.
    add_prefix: tuple[str, ...]
    env_flag: str


# Claude Code defaults to "local" scope (one project); "user" makes mneva
# available in every project. Its -e flag is variadic, so it must come after
# the server name or it swallows the name.
CLAUDE_CODE = AgentClient(
    "Claude Code", "claude", "claude-code", ("mcp", "add", "--scope", "user"), "-e"
)
CODEX = AgentClient("Codex", "codex", "codex", ("mcp", "add"), "--env")
CLIENTS = (CLAUDE_CODE, CODEX)


def server_argv(method: str | None = None) -> list[str]:
    """The command an agent should run to start mneva's MCP server."""
    if (method or detect_install_method()) == UVX:
        # uvx runs from a disposable cache dir, so sys.executable is not a
        # stable path. `--from` is required: bare `uvx mneva-mcp` fails.
        return ["uvx", "--from", "mneva", "mneva-mcp"]
    # The running interpreter works even when the mneva-mcp script is not on
    # the agent's PATH (editable installs, Windows user-site installs).
    return [sys.executable, "-m", "mneva.mcp_server"]


def add_argv(client: AgentClient, exe_path: str, server: list[str]) -> list[str]:
    return [
        exe_path, *client.add_prefix, SERVER_NAME,
        client.env_flag, f"MNEVA_MCP_CLIENT={client.client_id}",
        "--", *server,
    ]


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_CLI_TIMEOUT_SECONDS,
        check=False,
    )


def _register(client: AgentClient, server: list[str], *, dry_run: bool) -> bool:
    """Register mneva with one client. Returns False only on a failure."""
    # The full path matters on Windows: CreateProcess does not find .cmd
    # shims such as claude.CMD by bare name.
    exe_path = shutil.which(client.exe)
    if exe_path is None:
        click.echo(f"{client.label}: not found on PATH, skipped")
        return True
    argv = add_argv(client, exe_path, server)
    try:
        # Exit codes, not output text: the CLIs' wording changes by version.
        if _run([exe_path, "mcp", "get", SERVER_NAME]).returncode == 0:
            click.echo(f"{client.label}: already registered, left unchanged")
            return True
        if dry_run:
            click.echo(f"{client.label}: would run {subprocess.list2cmdline(argv)}")
            return True
        result = _run(argv)
    except (OSError, subprocess.SubprocessError) as e:
        click.echo(f"{client.label}: failed ({e})")
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit status {result.returncode}"
        click.echo(f"{client.label}: failed ({detail})")
        return False
    click.echo(f"{client.label}: added")
    return True


def _write_template(*, dry_run: bool) -> Path:
    template = mneva_home() / PROFILE_TEMPLATE_NAME
    if template.exists():
        click.echo(f"Profile template: {template} already exists, left unchanged")
    elif dry_run:
        click.echo(f"Profile template: would write {template}")
    else:
        ensure_home()
        template.write_text(PROFILE_TEMPLATE, encoding="utf-8")
        click.echo(f"Profile template: wrote {template}")
    return template


def _next_steps(template: Path) -> str:
    return f"""
Next steps:
  1. Fill in {template}.
  2. In Claude Code or Codex, say: "Read {template} and save each section
     to mneva with capture_memory, scope profile, lifespan permanent."
     One record per section lets a short brief drop a whole section
     instead of cutting one in half.
  3. Check it: mneva brief
     For tools without MCP: mneva brief --copy --for chatgpt (or doubao, gemini),
     then paste into that tool's "about you" setting. mneva reminds you when
     a pasted copy goes out of date.
  4. Restart Claude Code or Codex. mneva tells them to read your profile
     at the start of each conversation; if one skips it, say "read my mneva profile".
"""


@click.command("setup")
@click.option(
    "--dry-run", is_flag=True, help="Show what setup would do without changing anything."
)
def setup_command(dry_run: bool) -> None:
    """Connect mneva to Claude Code and Codex, and create a profile template."""
    server = server_argv()
    # Evaluate every client before failing, so one broken CLI does not hide
    # the state of the other.
    results = [_register(client, server, dry_run=dry_run) for client in CLIENTS]
    template = _write_template(dry_run=dry_run)
    click.echo(_next_steps(template))
    if not all(results):
        raise click.ClickException("some agents could not be registered; see above")
