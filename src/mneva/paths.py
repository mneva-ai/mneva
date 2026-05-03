from __future__ import annotations

import os
from pathlib import Path

_SUBDIRS = ("store", "index", "adr", "templates")


def mneva_home() -> Path:
    """Return the data root, honouring the $MNEVA_HOME env override."""
    override = os.environ.get("MNEVA_HOME")
    return Path(override).expanduser() if override else Path.home() / ".mneva"


def ensure_home() -> Path:
    """Create the data root and all required subdirectories. Idempotent."""
    home = mneva_home()
    home.mkdir(parents=True, exist_ok=True)
    for sub in _SUBDIRS:
        (home / sub).mkdir(exist_ok=True)
    return home
