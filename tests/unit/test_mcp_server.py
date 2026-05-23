"""Unit tests for ``mneva.mcp_server`` — each FastMCP tool called directly.

FastMCP's ``@mcp.tool()`` decorator leaves the underlying function callable as
a plain Python function. We exercise the tools that way so the tests run
without spawning a subprocess or a JSON-RPC loop. The stdio protocol round-trip
is covered separately in ``tests/integration/test_mcp_protocol.py``.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from mneva import mcp_server
from mneva.mcp_server import (
    capture_memory,
    forget_memory,
    get_status,
    list_recent_memories,
    replay_context,
    search_memory,
)
from mneva.store import Record


@pytest.fixture(autouse=True)
def _reset_mcp_singletons() -> Iterator[None]:
    """Each test gets a fresh module-level Indexer singleton."""
    mcp_server._indexer = None
    yield
    mcp_server._indexer = None


# ----------------------------- capture_memory --------------------------------


def test_capture_memory_happy_path(tmp_mneva_home: Path) -> None:
    result = capture_memory(scope="proj-a", body="decision: use sqlite")
    assert "id" in result
    assert len(result["id"]) == 16
    assert "summary" in result
    assert "Captured" in result["summary"]
    assert "decision: use sqlite" in result["summary"]
    assert result["record"]["scope"] == "proj-a"
    assert result["record"]["lifespan"] == "transient"
    # Record file actually materialized on disk.
    assert (tmp_mneva_home / "store" / f"{result['id']}.md").exists()


def test_capture_memory_refuses_empty_body(tmp_mneva_home: Path) -> None:
    result = capture_memory(scope="proj-a", body="")
    assert "error" in result
    assert "body" in result["summary"].lower()


def test_capture_memory_refuses_empty_scope(tmp_mneva_home: Path) -> None:
    result = capture_memory(scope="   ", body="x")
    assert "error" in result
    assert "scope" in result["summary"].lower()


def test_capture_memory_refuses_invalid_lifespan(tmp_mneva_home: Path) -> None:
    result = capture_memory(scope="proj-a", body="x", lifespan="forever")
    assert "error" in result
    assert "lifespan" in result["summary"].lower()


def test_capture_memory_persists_lifespan_and_source(tmp_mneva_home: Path) -> None:
    result = capture_memory(
        scope="proj-a", body="rule: be kind", lifespan="permanent", source="readme"
    )
    assert result["record"]["lifespan"] == "permanent"
    assert result["record"]["source"] == "readme"


# ------------------------------ search_memory --------------------------------


def test_search_memory_finds_captured(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="decision: use sqlite for v0")
    capture_memory(scope="proj-a", body="rule: ship a vertical slice")
    result = search_memory(query="sqlite")
    assert len(result["hits"]) == 1
    assert "sqlite" in result["hits"][0]["body"]
    assert "Found" in result["summary"]


def test_search_memory_filters_by_scope(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="decision: use sqlite for v0")
    capture_memory(scope="proj-b", body="decision: use sqlite for backend")
    result = search_memory(query="sqlite", scope="proj-a")
    assert len(result["hits"]) == 1
    assert result["hits"][0]["scope"] == "proj-a"


def test_search_memory_empty_result(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="decision: use sqlite")
    result = search_memory(query="postgres")
    assert result["hits"] == []
    assert "No memories matched" in result["summary"]


def test_search_memory_refuses_empty_query(tmp_mneva_home: Path) -> None:
    result = search_memory(query="")
    assert result["hits"] == []
    assert "Search refused" in result["summary"]


# ------------------------------ forget_memory --------------------------------


def test_forget_memory_removes_record(tmp_mneva_home: Path) -> None:
    captured = capture_memory(scope="proj-a", body="decision: use sqlite")
    result = forget_memory(record_id=captured["id"])
    assert result["ok"] is True
    assert "Forgot" in result["summary"]
    # Subsequent search no longer returns it.
    assert search_memory(query="sqlite")["hits"] == []


def test_forget_memory_unknown_id(tmp_mneva_home: Path) -> None:
    result = forget_memory(record_id="not-a-real-id")
    assert result["ok"] is False
    assert "No memory found" in result["summary"]


# -------------------------- list_recent_memories -----------------------------


def test_list_recent_memories_empty(tmp_mneva_home: Path) -> None:
    result = list_recent_memories()
    assert result["memories"] == []
    assert "No memories" in result["summary"]


def test_list_recent_memories_returns_records(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="first capture")
    capture_memory(scope="proj-a", body="second capture")
    result = list_recent_memories()
    assert len(result["memories"]) == 2


def test_list_recent_memories_filters_by_scope(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="alpha record")
    capture_memory(scope="proj-b", body="beta record")
    result = list_recent_memories(scope="proj-b")
    assert len(result["memories"]) == 1
    assert result["memories"][0]["scope"] == "proj-b"


# ------------------------------ replay_context -------------------------------


def test_replay_context_returns_markdown(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="rule: be honest", lifespan="permanent")
    out = replay_context(tool="claude-code")
    assert isinstance(out, str)
    assert "Captured records" in out
    assert "rule: be honest" in out


def test_replay_context_unknown_tool_returns_friendly_error(
    tmp_mneva_home: Path,
) -> None:
    out = replay_context(tool="not-a-real-tool")
    assert "unknown tool" in out


# -------------------------------- get_status ---------------------------------


def test_get_status_returns_count_and_mode(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="first")
    capture_memory(scope="proj-a", body="second")
    result = get_status()
    assert result["count"] == 2
    assert result["mode"] in {"bm25", "sqlite-vec"}
    assert result["client"] == "mcp"  # MNEVA_MCP_CLIENT unset
    assert str(tmp_mneva_home) in result["home"]
    assert "wired up" in result["summary"]


# ============================ IRON regressions ===============================
# Locked by /plan-eng-review (D1, D2) and /plan-ceo-review (F1 attribution).


def test_auto_init_materializes_home_and_config_on_first_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D1: mneva-mcp starts cleanly without a prior `mneva init` run."""
    fresh_home = tmp_path / "fresh-home"
    assert not fresh_home.exists()
    monkeypatch.setenv("MNEVA_HOME", str(fresh_home))

    mcp_server._auto_init()

    assert fresh_home.exists()
    assert (fresh_home / "store").exists()
    assert (fresh_home / "config.json").exists()


def test_mneva_mcp_client_env_attributes_records(
    tmp_mneva_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1: MNEVA_MCP_CLIENT env var attributes captured records per client."""
    monkeypatch.setenv("MNEVA_MCP_CLIENT", "claude-desktop")
    captured = capture_memory(scope="proj-a", body="env attribution test")
    assert captured["record"]["tool"] == "claude-desktop"

    # Attribution log line written too.
    log_path = tmp_mneva_home / ".mcp-attribution.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "claude-desktop" in content


def test_record_to_dict_round_trip_stable() -> None:
    """D2: Record.to_dict carries every public field, ordering stable."""
    rec = Record(
        id="abc123",
        scope="proj-a",
        lifespan="permanent",
        tool="claude-desktop",
        body="hello",
        source="readme",
    )
    d = rec.to_dict()
    assert set(d.keys()) == {"id", "scope", "lifespan", "tool", "body", "source"}
    assert d == {
        "id": "abc123",
        "scope": "proj-a",
        "lifespan": "permanent",
        "tool": "claude-desktop",
        "body": "hello",
        "source": "readme",
    }
