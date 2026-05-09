from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mneva.api import create_app
from mneva.config import Config
from mneva.paths import ensure_home


@pytest.fixture
def client(tmp_mneva_home: Path) -> TestClient:
    home = ensure_home()
    cfg = Config(token="t" * 32)
    app = create_app(home=home, config=cfg)
    return TestClient(app)


def test_status_requires_token(client: TestClient) -> None:
    r = client.get("/status")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing or invalid X-MNEVA-Token"


def test_status_accepts_correct_token(client: TestClient) -> None:
    r = client.get("/status", headers={"X-MNEVA-Token": "t" * 32})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] in {"sqlite-vec", "bm25"}
    assert body["count"] == 0


def _h(token: str = "t" * 32) -> dict[str, str]:
    return {"X-MNEVA-Token": token}


def test_capture_creates_record(client: TestClient, tmp_mneva_home: Path) -> None:
    r = client.post(
        "/capture",
        json={
            "scope": "ticket-1",
            "tool": "cursor",
            "lifespan": "permanent",
            "body": "hello api",
        },
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    assert (tmp_mneva_home / "store" / f"{rid}.md").exists()


def test_forget_deletes_record(client: TestClient, tmp_mneva_home: Path) -> None:
    r = client.post(
        "/capture",
        json={"scope": "s", "tool": "cli", "lifespan": "transient", "body": "bye"},
        headers=_h(),
    )
    rid = r.json()["id"]
    r2 = client.post("/forget", json={"id": rid}, headers=_h())
    assert r2.status_code == 200
    assert r2.json() == {"forgot": rid}
    assert not (tmp_mneva_home / "store" / f"{rid}.md").exists()


def test_search_returns_hits(client: TestClient) -> None:
    client.post(
        "/capture",
        json={"scope": "s", "tool": "cli", "lifespan": "permanent", "body": "alpha bravo"},
        headers=_h(),
    )
    r = client.get("/search", params={"q": "alpha"}, headers=_h())
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert any("alpha bravo" in h["body"] for h in hits)


def test_replay_returns_context_block_for_tool(client: TestClient) -> None:
    client.post(
        "/capture",
        json={
            "scope": "ticket-9",
            "tool": "cursor",
            "lifespan": "permanent",
            "body": "decision: use BM25 fallback first",
        },
        headers=_h(),
    )
    r = client.get(
        "/replay",
        params={"tool": "claude-code", "scope": "ticket-9"},
        headers=_h(),
    )
    assert r.status_code == 200
    block = r.text
    assert "decision: use BM25 fallback first" in block
    assert "ticket-9" in block
