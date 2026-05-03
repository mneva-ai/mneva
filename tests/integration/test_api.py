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
