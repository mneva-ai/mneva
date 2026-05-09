from __future__ import annotations

import hashlib
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from mneva.config import Config
from mneva.indexer import Indexer
from mneva.paths import ensure_home
from mneva.store import Record, forget_record, write_record


class CaptureBody(BaseModel):
    scope: str
    tool: str
    lifespan: str
    body: str
    source: str | None = None


class ForgetBody(BaseModel):
    id: str


def _new_id(scope: str, body: str) -> str:
    raw = f"{scope}|{time.time_ns()}|{body[:64]}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def create_app(home: Path | None = None, config: Config | None = None) -> FastAPI:
    if home is None:
        home = ensure_home()
    if config is None:
        from mneva.config import load_config

        config = load_config(home)

    app = FastAPI(title="Mneva", version="0.1.0a1")
    expected_token = config.token
    resolved_home: Path = home

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
        idx = Indexer(resolved_home / "mneva.sqlite")
        return idx.status()

    @app.post("/capture")
    def capture(req: CaptureBody) -> dict[str, str]:
        rec = Record(
            id=_new_id(req.scope, req.body),
            scope=req.scope,
            lifespan=req.lifespan,
            tool=req.tool,
            body=req.body,
            source=req.source,
        )
        write_record(rec, home=resolved_home)
        Indexer(resolved_home / "mneva.sqlite").add(rec)
        return {"id": rec.id}

    @app.post("/forget")
    def forget(req: ForgetBody) -> dict[str, str]:
        existed = forget_record(req.id, home=resolved_home)
        Indexer(resolved_home / "mneva.sqlite").remove(req.id)
        if not existed:
            raise HTTPException(status_code=404, detail=f"no such record: {req.id}")
        return {"forgot": req.id}

    @app.get("/search")
    def search(
        q: str = Query(...),
        scope: str | None = Query(None),
        lifespan: str | None = Query(None),
        k: int = Query(10),
    ) -> dict[str, list[dict[str, str]]]:
        idx = Indexer(resolved_home / "mneva.sqlite")
        hits = idx.search(q, scope=scope, lifespan=lifespan, k=k)
        return {
            "hits": [
                {"id": r.id, "scope": r.scope, "tool": r.tool, "body": r.body}
                for r in hits
            ]
        }

    @app.get("/replay", response_class=PlainTextResponse)
    def replay(
        tool: str = Query(...),
        scope: str | None = Query(None),
    ) -> str:
        from mneva.replay import VALID_TOOLS, render_replay

        if tool not in VALID_TOOLS:
            raise HTTPException(
                status_code=400,
                detail=f"unsupported tool: {tool!r}  (valid: {', '.join(sorted(VALID_TOOLS))})",
            )
        return render_replay(tool=tool, scope=scope, home=resolved_home)

    return app
