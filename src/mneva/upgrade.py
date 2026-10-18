"""`mneva upgrade` — update mneva to the latest published version.

mneva can be installed several ways (pipx, ``uv tool``, ``uvx``, or plain
``pip``). Each has a different upgrade command, and remembering which one you
used is exactly the friction this command removes: run ``mneva upgrade`` and it
figures out how the running interpreter was installed and runs the right thing.

Detection keys off ``sys.prefix`` (the environment root of the running
interpreter). The mapping is deliberately conservative: when we cannot tell, we
fall back to ``pip``, which is correct for plain virtualenv / system installs
and harmless to suggest otherwise. The detection and command-planning halves are
split into pure functions so they can be unit-tested without spawning a
subprocess.

After the package update, the command runs ``mneva setup --after-upgrade`` in a
new process, so the new version refreshes what setup installed (the browser
extension copy, the native host launcher) and the user has one step, not three.

  sys.prefix ──▶ detect_install_method ──▶ method ──▶ plan_for ──▶ UpgradePlan
                       │                                              │
                       ▼                                              ▼
                 ".../pipx/..."  -> PIPX                     command + message
                 ".../uv/tools/" -> UV_TOOL                  (command is None for
                 ".../uv/cache/" -> UVX (ephemeral)           the ephemeral uvx
                  anything else  -> PIP                       case: nothing to run)
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

import click

# Install methods we can distinguish.
PIPX = "pipx"
UV_TOOL = "uv-tool"
UVX = "uvx"
PIP = "pip"


@dataclass(frozen=True, slots=True)
class UpgradePlan:
    """How to upgrade for a detected install method.

    ``command`` is the argv to run, or ``None`` when there is nothing to run
    (an ephemeral ``uvx`` invocation already fetches the latest version).
    ``message`` is the human-readable line printed before acting.
    """

    method: str
    command: list[str] | None
    message: str


def detect_install_method(prefix: str | None = None) -> str:
    """Classify how mneva is installed from the interpreter's ``sys.prefix``.

    Returns one of :data:`PIPX`, :data:`UV_TOOL`, :data:`UVX`, :data:`PIP`.
    Falls back to :data:`PIP` when the prefix matches none of the markers.
    ``prefix`` is injectable so tests can exercise every branch without
    needing the real install layout.
    """
    raw = prefix if prefix is not None else sys.prefix
    norm = raw.replace("\\", "/").lower()
    if "pipx" in norm:
        return PIPX
    if "/uv/tools/" in norm:
        return UV_TOOL
    # uvx runs out of uv's cache; the layout differs per-OS but always lives
    # under a uv cache dir or an "archive-v*" environment.
    if "/uv/cache" in norm or "/.cache/uv" in norm or "archive-v" in norm:
        return UVX
    return PIP


def plan_for(method: str) -> UpgradePlan:
    """Map a detected install method to its upgrade plan."""
    if method == PIPX:
        return UpgradePlan(
            PIPX,
            ["pipx", "upgrade", "mneva"],
            "Detected pipx install. Running: pipx upgrade mneva",
        )
    if method == UV_TOOL:
        return UpgradePlan(
            UV_TOOL,
            ["uv", "tool", "upgrade", "mneva"],
            "Detected uv tool install. Running: uv tool upgrade mneva",
        )
    if method == UVX:
        return UpgradePlan(
            UVX,
            None,
            "Detected uvx (ephemeral) run. uvx always fetches the latest "
            "published version, so there is nothing to upgrade. If you pinned "
            "a version, run: uvx mneva@latest",
        )
    return UpgradePlan(
        PIP,
        [sys.executable, "-m", "pip", "install", "--upgrade", "mneva"],
        "Running: pip install --upgrade mneva",
    )


def setup_refresh_argv() -> list[str]:
    """Run setup in a new process: this one still runs the replaced version."""
    return [sys.executable, "-m", "mneva.cli", "setup", "--after-upgrade"]


@click.command("upgrade")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show how mneva would update without running anything.",
)
def upgrade_command(dry_run: bool) -> None:
    """Update mneva to the latest published version.

    Detects how mneva was installed (pipx, uv tool, uvx, or pip) and runs the
    matching upgrade command, so you don't have to remember which one you used.
    Then refreshes what `mneva setup` installed. Use --dry-run to see the
    commands first.
    """
    plan = plan_for(detect_install_method())
    click.echo(plan.message)
    if dry_run:
        if plan.command is not None:
            click.echo(f"(dry-run) would run: {' '.join(plan.command)}")
        click.echo("(dry-run) would then run: mneva setup --after-upgrade")
        return
    if plan.command is not None:
        try:
            result = subprocess.run(plan.command, check=False)  # noqa: S603
        except FileNotFoundError as e:
            raise click.ClickException(
                f"could not find '{plan.command[0]}' on PATH. "
                f"Update manually with: {' '.join(plan.command)}"
            ) from e
        if result.returncode != 0:
            raise click.ClickException(f"upgrade command exited with status {result.returncode}")
    # Even with nothing to update (uvx), the extension copy may predate this version.
    if subprocess.run(setup_refresh_argv(), check=False).returncode != 0:  # noqa: S603
        raise click.ClickException(
            "mneva was updated, but refreshing its setup failed (see above). Run: mneva setup"
        )
    click.echo("mneva upgrade complete. Run `mneva --version` to confirm.")
