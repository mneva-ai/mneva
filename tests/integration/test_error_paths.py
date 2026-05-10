from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "mneva.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_synthesize_missing_api_key(tmp_mneva_home: Path) -> None:
    run_cli("init")

    # Strip ANTHROPIC_API_KEY so MissingAPIKeyError fires even if the user has it set.
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    result = run_cli("synthesize", "--scope=anything", "--backend=anthropic", env=env)
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "missing API key for anthropic" in combined
    assert "ANTHROPIC_API_KEY" in combined


def test_serve_port_collision(tmp_mneva_home: Path) -> None:
    run_cli("init")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)  # mneva's _port_in_use uses connect_ex; a bound-but-not-listening socket would refuse and look free
        port = s.getsockname()[1]

        result = run_cli("serve", f"--port={port}")

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert f"port {port} is already in use" in combined


def test_forget_nonexistent_record(tmp_mneva_home: Path) -> None:
    run_cli("init")

    result = run_cli("forget", "abc123def4567890", "--confirm")
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "no such record: abc123def4567890" in combined


def test_capture_missing_body(tmp_mneva_home: Path) -> None:
    run_cli("init")

    result = run_cli("capture", "--scope=s")
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "body required" in combined
    assert "'-' for stdin" in combined
