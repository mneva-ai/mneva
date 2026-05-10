from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"server on port {port} did not become ready within {timeout}s")


@pytest.fixture()
def live_server(tmp_mneva_home: Path) -> Iterator[tuple[str, str]]:
    # Init to create config.json
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "mneva.cli", "init"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    token: str = json.loads((tmp_mneva_home / "config.json").read_text())["token"]
    port = _free_port()

    popen_kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "mneva.cli", "serve", "--port", str(port), "--host", "127.0.0.1"],
        **popen_kwargs,
    )

    try:
        _wait_ready(port)
        yield f"http://127.0.0.1:{port}", token
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def test_endpoints_happy_path(live_server: tuple[str, str]) -> None:
    base_url, token = live_server
    client = httpx.Client(base_url=base_url, headers={"X-MNEVA-Token": token})

    # POST /capture
    r = client.post("/capture", json={
        "scope": "t82",
        "tool": "cursor",
        "lifespan": "permanent",
        "body": "HTTP marker T8.2",
    })
    assert r.status_code == 200
    mem_id: str = r.json()["id"]
    assert len(mem_id) == 16

    # GET /status
    r = client.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["mode"] in {"sqlite-vec", "bm25"}

    # GET /search
    r = client.get("/search", params={"q": "marker", "scope": "t82"})
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert any("HTTP marker T8.2" in h["body"] for h in hits)

    # GET /replay (PlainTextResponse)
    r = client.get("/replay", params={"tool": "claude-code", "scope": "t82"})
    assert r.status_code == 200
    assert "--tool=claude-code" in r.text
    assert "HTTP marker T8.2" in r.text

    # POST /forget
    r = client.post("/forget", json={"id": mem_id})
    assert r.status_code == 200
    assert r.json() == {"forgot": mem_id}


def test_unauthorized_returns_401(live_server: tuple[str, str]) -> None:
    base_url, _token = live_server
    r = httpx.get(base_url + "/status")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing or invalid X-MNEVA-Token"
