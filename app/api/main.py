"""FastAPI backend for The Last Satellite (contract: docs/ARCHITECTURE.md)."""
from __future__ import annotations

import csv
import io
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from app.api import store
from app.common.config import load_config
from app.common.paths import EVAL_DIR

app = FastAPI(title="The Last Satellite: Mission Memory Engine", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "models": store.model_status()}


@app.get("/config")
def config():
    return load_config()


@app.get("/mission")
def mission():
    return store.mission()


@app.get("/channels")
def channels():
    return store.channels()


@app.get("/channels/{ch}/telemetry")
def channel_telemetry(ch: str, start: str | None = None, end: str | None = None,
                      max_points: int = Query(5000, le=50000)):
    out = store.channel_telemetry(ch, start, end, max_points)
    if out is None:
        raise HTTPException(404, f"unknown channel {ch}")
    return out


@app.get("/segments")
def segments(split: str | None = "test", sort: str = "probability", limit: int = 100,
             status: str | None = None):
    return store.list_segments(split, sort, limit, status)


@app.get("/segments/{segment_id}")
def segment(segment_id: int, reveal: bool = False):
    out = store.segment_detail(segment_id, reveal)
    if out is None:
        raise HTTPException(404, "segment not found")
    return out


@app.get("/segments/{segment_id}/features")
def segment_features(segment_id: int):
    out = store.segment_features(segment_id)
    if out is None:
        raise HTTPException(404, "segment not found")
    return out


# ---- evaluations (Model Laboratory reads ONLY these) -------------------------
@app.get("/evaluations")
def evaluations():
    items = []
    for p in sorted(EVAL_DIR.iterdir()):
        if p.is_file() and not p.name.startswith("."):
            meta = {}
            if p.suffix == ".json":
                try:
                    d = json.loads(p.read_text())
                    meta = {k: d.get(k) for k in ("produced_by", "created_at", "git_sha")}
                except Exception:
                    pass
            items.append({"name": p.name, "kind": p.suffix.lstrip("."), **meta})
    return items


@app.get("/evaluations/{name}")
def evaluation(name: str):
    p = (EVAL_DIR / name).resolve()
    if EVAL_DIR.resolve() not in p.parents or not p.exists():
        raise HTTPException(404, "not yet measured")
    if p.suffix == ".json":
        return json.loads(p.read_text())
    if p.suffix == ".jsonl":
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    if p.suffix == ".csv":
        rows = list(csv.DictReader(io.StringIO(p.read_text())))
        return {"columns": list(rows[0].keys()) if rows else [], "rows": rows}
    if p.suffix == ".md":
        return {"markdown": p.read_text()}
    if p.suffix == ".png":
        return FileResponse(p, media_type="image/png")
    return Response(p.read_bytes(), media_type="application/octet-stream")
