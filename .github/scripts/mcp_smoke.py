"""MCP stdio smoke check for install-verify.yml.

Spawns the installed ``mneva-mcp`` console script and exercises the MCP stdio
protocol: initialize -> list_tools -> assert the six v0.2 tools are present.

Run from the install-verify workflow AFTER ``pipx install mneva`` has put
``mneva-mcp`` on PATH. Requires the ``mcp`` SDK to be installed in the same
Python environment that runs this script (workflow handles that).
"""
from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "capture_memory",
    "search_memory",
    "forget_memory",
    "list_recent_memories",
    "replay_context",
    "get_status",
}


async def main() -> int:
    params = StdioServerParameters(
        command="mneva-mcp",
        args=[],
        env={"MNEVA_MCP_CLIENT": "install-verify"},
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        result = await session.list_tools()
        names = {tool.name for tool in result.tools}
        missing = EXPECTED_TOOLS - names
        if missing:
            print(f"FAIL: missing tools: {sorted(missing)}", file=sys.stderr)
            return 1
        print(f"OK: mneva-mcp exposes all {len(EXPECTED_TOOLS)} expected tools")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
