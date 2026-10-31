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


# ---- prediction, similarity, investigations ------------------------------------
from app.api.schemas import AskIn, ExtractIn, FeedbackIn, InvestigateIn, PredictIn  # noqa: E402


@app.post("/predict")
def predict(body: PredictIn):
    from app.prediction.service import predict_raw, predict_segment
    if body.segment_id is not None:
        out = predict_segment(body.segment_id)
        if out is None:
            raise HTTPException(404, "no prediction for segment")
        out.pop("source", None)
        return out
    if not (body.channel and body.sampling and body.t and body.v):
        raise HTTPException(422, "give segment_id, or channel+sampling+t+v")
    return predict_raw(body.channel, body.sampling, body.t, body.v)


@app.get("/segments/{segment_id}/similar")
def segment_similar(segment_id: int, k: int = 5):
    from app.memory.similar import similar
    return similar(segment_id, k)


@app.post("/investigations")
def create_investigation(body: InvestigateIn):
    from app.investigation.builder import build_card
    if store.segment_row(body.segment_id) is None:
        raise HTTPException(404, "segment not found")
    return build_card(body.segment_id, body.use_lm)


@app.get("/investigations")
def investigations(status: str | None = None):
    from app.investigation.builder import list_cards
    return list_cards(status)


@app.get("/investigations/{card_id}")
def investigation(card_id: str):
    from app.investigation.builder import get_card
    c = get_card(card_id)
    if c is None:
        raise HTTPException(404, "card not found")
    return c


@app.post("/investigations/{card_id}/feedback")
def investigation_feedback(card_id: str, body: FeedbackIn):
    from app.investigation.builder import feedback
    c = feedback(card_id, body.action, body.note)
    if c is None:
        raise HTTPException(404, "card not found")
    return c


@app.post("/investigations/{card_id}/reveal")
def investigation_reveal(card_id: str):
    from app.investigation.builder import reveal
    c = reveal(card_id)
    if c is None:
        raise HTTPException(404, "card not found")
    return c


# ---- mission memory ------------------------------------------------------------
@app.post("/memory/ask")
def memory_ask(body: AskIn):
    from app.memory.qa import answer
    return answer(body.question, body.k)


@app.post("/memory/extract")
def memory_extract(body: ExtractIn):
    from app.memory.extract import extract
    return extract(body.text)


@app.get("/memory/timeline")
def memory_timeline():
    return store.mission()["timeline"]


@app.get("/documents")
def documents():
    return store.documents()


@app.get("/documents/{doc_id}")
def document(doc_id: str):
    d = store.document(doc_id)
    if d is None:
        raise HTTPException(404, "document not found")
    return d


# ---- guided demo + export --------------------------------------------------------
@app.get("/demo")
def demo():
    from app.investigation.demo import load
    return [{"segment_id": i["segment_id"], "blurb": i["blurb"]} for i in load()["items"]]


@app.get("/demo/{segment_id}/steps")
def demo_steps(segment_id: int):
    from app.investigation.builder import build_card
    from app.investigation.demo import load
    from app.memory.similar import similar
    from app.prediction.service import predict_segment
    if segment_id not in {i["segment_id"] for i in load()["items"]}:
        raise HTTPException(404, "not a demo segment")
    detail = store.segment_detail(segment_id, reveal=False)
    pred = predict_segment(segment_id); pred.pop("source", None)
    card = build_card(segment_id, use_lm=True)
    return {**detail, "features": store.segment_features(segment_id), "prediction": pred,
            "citations": card["documents"], "similar": similar(segment_id, 5), "card": card}


@app.get("/demo/{segment_id}/reveal")
def demo_reveal(segment_id: int):
    from app.investigation.demo import load
    d = load()
    item = next((i for i in d["items"] if i["segment_id"] == segment_id), None)
    if item is None:
        raise HTTPException(404, "not a demo segment")
    return {"segment_id": segment_id, "label": item["label"], "case": item["case"],
            "predicted": int(item["probability"] >= d["threshold"]), "probability": item["probability"],
            "threshold": d["threshold"]}


@app.get("/export")
def export():
    from app.investigation.export import build_zip
    return Response(build_zip(), media_type="application/zip",
                    headers={"Content-Disposition": "attachment; filename=mission_memory_archive.zip"})
