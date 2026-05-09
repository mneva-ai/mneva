from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_e2e_cli_happy_path(tmp_mneva_home: Path) -> None:
    def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, "-m", "mneva.cli", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    # 1. init
    result = run_cli("init")
    assert result.returncode == 0, result.stderr
    assert (tmp_mneva_home / "config.json").exists()

    # 2. capture
    result = run_cli(
        "capture", "--scope=e2e", "--lifespan=permanent", "T8.1 e2e marker body"
    )
    assert result.returncode == 0, result.stderr
    record_id = result.stdout.strip().splitlines()[-1]
    assert len(record_id) == 16

    # 3. status sanity — confirms indexer wrote one record
    result = run_cli("status")
    assert result.returncode == 0, result.stderr
    assert "count: 1" in result.stdout

    # 4. search
    result = run_cli("search", "e2e marker")
    assert result.returncode == 0, result.stderr
    assert record_id in result.stdout
    assert "T8.1 e2e marker body" in result.stdout

    # 5. replay
    result = run_cli("replay", "--tool=claude-code", "--scope=e2e")
    assert result.returncode == 0, result.stderr
    assert "--tool=claude-code" in result.stdout
    assert "T8.1 e2e marker body" in result.stdout

    # 6. forget
    result = run_cli("forget", record_id, "--confirm")
    assert result.returncode == 0, result.stderr
    assert f"forgot: {record_id}" in result.stdout
    assert not (tmp_mneva_home / "store" / f"{record_id}.md").exists()
