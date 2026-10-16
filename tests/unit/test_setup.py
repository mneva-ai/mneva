from __future__ import annotations

import sys

from mneva import setup
from mneva.setup import CLAUDE_CODE, CODEX, add_argv, server_argv
from mneva.upgrade import PIP, PIPX, UVX


def test_server_argv_uses_running_interpreter_for_installed_mneva() -> None:
    # Works for pip, pipx, uv tool and editable installs alike, even when the
    # mneva-mcp script is not on the agent's PATH.
    assert server_argv(PIP) == [sys.executable, "-m", "mneva.mcp_server"]
    assert server_argv(PIPX) == [sys.executable, "-m", "mneva.mcp_server"]


def test_server_argv_for_uvx_names_the_package() -> None:
    # uvx's environment is a disposable cache dir; bare `uvx mneva-mcp`
    # resolves mneva-mcp as a package and fails.
    assert server_argv(UVX) == ["uvx", "--from", "mneva", "mneva-mcp"]


def test_claude_code_add_registers_user_scope_with_attribution() -> None:
    argv = add_argv(CLAUDE_CODE, "C:/bin/claude.CMD", ["py", "-m", "mneva.mcp_server"])

    assert argv == [
        "C:/bin/claude.CMD", "mcp", "add", "--scope", "user", setup.SERVER_NAME,
        "-e", "MNEVA_MCP_CLIENT=claude-code", "--", "py", "-m", "mneva.mcp_server",
    ]


def test_codex_add_sets_attribution() -> None:
    argv = add_argv(CODEX, "codex", ["mneva-mcp"])

    assert argv == [
        "codex", "mcp", "add", setup.SERVER_NAME,
        "--env", "MNEVA_MCP_CLIENT=codex", "--", "mneva-mcp",
    ]
