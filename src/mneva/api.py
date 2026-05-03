from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mneva.config import Config
from mneva.indexer import Indexer
from mneva.paths import ensure_home


def create_app(home: Path | None = None, config: Config | None = None) -> FastAPI:
    if home is None:
        home = ensure_home()
    if config is None:
        from mneva.config import load_config

        config = load_config(home)

    app = FastAPI(title="Mneva", version="0.1.0a1")
    expected_token = config.token

    @app.middleware("http")
    async def auth(request: Request, call_next):  # type: ignore[no-untyped-def]
        token = request.headers.get("X-MNEVA-Token")
        if token != expected_token:
            return JSONResponse(
                status_code=401,
                content={"detail": "missing or invalid X-MNEVA-Token"},
            )
        return await call_next(request)

    @app.get("/status")
    def status() -> dict[str, int | str]:
        idx = Indexer(home / "mneva.sqlite")
        return idx.status()

    return app
