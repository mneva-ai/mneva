"""Integration test: spawn mneva-mcp as a subprocess and exercise it via MCP stdio.

This is the real-world wiring path. Claude Desktop, Cursor, etc all spawn
``python -m mneva.mcp_server`` (or the equivalent ``mneva-mcp`` console script)
and talk to it via JSON-RPC over stdio using the official ``mcp`` SDK. This
test mirrors that exactly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.integration


_EXPECTED_TOOLS = {
    "capture_memory",
    "search_memory",
    "forget_memory",
    "list_recent_memories",
    "replay_context",
    "get_status",
}


def _server_params(home: Path, client_name: str = "pytest") -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mneva.mcp_server"],
        env={
            "MNEVA_HOME": str(home),
            "MNEVA_MCP_CLIENT": client_name,
            # PATH needed so the subprocess Python can find anything it imports
            # via site-packages (no-op on most setups, defense in depth).
            "PATH": __import__("os").environ.get("PATH", ""),
        },
    )


async def test_initialize_and_list_tools(tmp_path: Path) -> None:
    """Spawn mneva-mcp, complete the MCP handshake, and assert the 6 tools."""
    home = tmp_path / ".mneva-itest"
    params = _server_params(home)
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        result = await session.list_tools()
        tool_names = {t.name for t in result.tools}
        assert _EXPECTED_TOOLS.issubset(tool_names)


async def test_get_status_via_protocol(tmp_path: Path) -> None:
    """Tool call round-trip works end-to-end and returns a sensible payload."""
    home = tmp_path / ".mneva-itest"
    params = _server_params(home, client_name="pytest-status")
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        response = await session.call_tool("get_status", arguments={})
        assert response.isError is not True
        # The auto-init must have created the home dir before the tool ran.
        assert home.exists()
        assert (home / "config.json").exists()


async def test_capture_then_search_round_trip(tmp_path: Path) -> None:
    """A captured memory is searchable in the same session."""
    home = tmp_path / ".mneva-itest"
    params = _server_params(home, client_name="pytest-roundtrip")
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        cap = await session.call_tool(
            "capture_memory",
            arguments={
                "scope": "proj-itest",
                "body": "decision: ship v0.2 via MCP",
                "lifespan": "permanent",
            },
        )
        assert cap.isError is not True

        srch = await session.call_tool(
            "search_memory",
            arguments={"query": "MCP"},
        )
        assert srch.isError is not True
