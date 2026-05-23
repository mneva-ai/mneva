"""Tests for ``mneva.diagnose`` — opt-in observability render path.

The hard contract is "zero record content". The first test exists to fail
loudly if any future refactor causes record bodies / ids to leak into the
diagnose output.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from mneva import mcp_server
from mneva.diagnose import render_diagnose
from mneva.mcp_server import capture_memory


@pytest.fixture(autouse=True)
def _reset_mcp_singletons() -> Iterator[None]:
    mcp_server._indexer = None
    yield
    mcp_server._indexer = None


def test_diagnose_basic_output_contains_platform_python_home(
    tmp_mneva_home: Path,
) -> None:
    out = render_diagnose()
    assert "mneva diagnose" in out
    assert "platform:" in out
    assert "python:" in out
    assert "mneva home:" in out
    assert "records:" in out
    assert "backends configured:" in out
    assert "mcp clients seen:" in out


def test_diagnose_share_flag_adds_share_footer(tmp_mneva_home: Path) -> None:
    plain = render_diagnose(share=False)
    shared = render_diagnose(share=True)
    assert "copy the output above" in shared
    assert "copy the output above" not in plain


def test_diagnose_never_leaks_record_content(tmp_mneva_home: Path) -> None:
    """The CRITICAL contract: zero record body / id / source in diagnose output."""
    secret_body = "MY_SUPER_SENSITIVE_PASSPHRASE_12345"
    secret_source = "very-private-source-url"
    capture_memory(
        scope="proj-secret",
        body=secret_body,
        lifespan="permanent",
        source=secret_source,
    )
    out = render_diagnose(share=True)
    assert secret_body not in out
    assert secret_source not in out
    # Counts ARE allowed to leak.
    assert "1" in out  # the record count


def test_diagnose_counts_by_lifespan(tmp_mneva_home: Path) -> None:
    capture_memory(scope="proj-a", body="transient one")
    capture_memory(scope="proj-a", body="permanent one", lifespan="permanent")
    out = render_diagnose()
    assert "records: 2" in out
    assert "transient: 1" in out
    assert "permanent: 1" in out


def test_diagnose_parses_attribution_log(tmp_mneva_home: Path) -> None:
    log_path = tmp_mneva_home / ".mcp-attribution.log"
    log_path.write_text(
        json.dumps({"ts": "2026-05-22T12:00:00+00:00", "client": "claude-desktop", "action": "capture"})
        + "\n"
        + json.dumps({"ts": "2026-05-22T12:01:00+00:00", "client": "claude-desktop", "action": "search"})
        + "\n"
        + json.dumps({"ts": "2026-05-22T12:02:00+00:00", "client": "cursor", "action": "capture"})
        + "\n",
        encoding="utf-8",
    )
    out = render_diagnose()
    assert "claude-desktop (2)" in out
    assert "cursor (1)" in out
    assert "2026-05-22T12:02:00+00:00" in out


def test_diagnose_handles_no_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When home does not exist yet, diagnose still runs and reports missing."""
    fresh_home = tmp_path / "no-mneva-home"
    monkeypatch.setenv("MNEVA_HOME", str(fresh_home))
    out = render_diagnose()
    assert "missing" in out
    assert "records: 0" in out
