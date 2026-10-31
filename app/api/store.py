"""Read-side data access used by the API."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd
import yaml

from app.common.channels import CHANNELS
from app.common.paths import DOCS_DIR, EVAL_DIR, MODELS_DIR
from app.memory.db import connect
from app.telemetry.evidence import significant_gaps
from app.telemetry.features import EXTRA_NAMES, PUBLISHED_18, zero_runs

_con = None


def con():
    global _con
    if _con is None:
        _con = connect()
    return _con


def model_status() -> dict:
    return {"tabular": (MODELS_DIR / "tabpfn_final.pkl").exists(),
            "adapter": (MODELS_DIR / "adapter.gguf").exists()}


def _verification() -> dict:
    p = EVAL_DIR / "dataset_verification.json"
    return json.loads(p.read_text()) if p.exists() else {}


def mission() -> dict:
    v = _verification()
    tl_path = DOCS_DIR / "timeline.yaml"
    timeline = yaml.safe_load(tl_path.read_text()) if tl_path.exists() else []
    return {
        "name": "OPS-SAT",
        "operator": "European Space Agency (ESA)",
        "status": "archival",
        "reentry_date": "2024-05-22",
        "datasets": [{
            "name": "OPSSAT-AD", "doi": "10.5281/zenodo.12588359", "license": "CC-BY-4.0",
            "segments": v.get("segments_csv", {}).get("n_segments"),
            "train": v.get("split", {}).get("train"), "test": v.get("split", {}).get("test"),
            "anomaly_rate": v.get("anomaly_rate"),
        }],
        "channels": channels(),
        "timeline": timeline,
    }


def channels() -> list[dict]:
    rows = con().execute(
        "SELECT channel, COUNT(*) n, AVG(CASE WHEN split='train' THEN label END) ar "
        "FROM segments GROUP BY channel ORDER BY channel").fetchall()
    return [{"channel": r["channel"], "channel_name": CHANNELS[r["channel"]][0],
             "kind": CHANNELS[r["channel"]][1], "n_segments": r["n"],
             "anomaly_rate_train": round(r["ar"], 4)} for r in rows]


def _series(df: pd.DataFrame, segment_id, sampling: int) -> dict:
    ts = pd.to_datetime(df["timestamp"])
    v = df["value"].to_numpy(dtype=float)
    gp = significant_gaps(ts.reset_index(drop=True), sampling)
    return {
        "segment_id": segment_id,
        "t": df["timestamp"].tolist(),
        "v": v.tolist(),
        "gaps": [{"start": df["timestamp"].iloc[i - 1], "end": df["timestamp"].iloc[i], "seconds": s}
                 for i, s in gp],
        "zero_runs": [{"start_idx": s, "end_idx": e} for s, e in zero_runs(v, 2)],
        "peaks_idx": _peaks(v),
    }


def _peaks(v: np.ndarray) -> list[int]:
    import scipy.signal as sig
    if len(v) < 3 or v.max() == v.min():
        return []
    return sig.find_peaks(v, prominence=0.1 * (v.max() - v.min()))[0].tolist()


def segment_row(segment_id: int):
    return con().execute("SELECT * FROM segments WHERE segment_id=?", (segment_id,)).fetchone()


def segment_detail(segment_id: int, reveal: bool) -> dict | None:
    r = segment_row(segment_id)
    if r is None:
        return None
    seg = dict(r)
    if not reveal:
        seg["label"] = None
    df = pd.read_sql("SELECT timestamp, value FROM telemetry_points WHERE segment_id=? ORDER BY idx",
                     con(), params=(segment_id,))
    return {"segment": seg, "series": _series(df, segment_id, r["sampling"])}


def segment_values(segment_id: int) -> pd.DataFrame:
    return pd.read_sql("SELECT timestamp, value FROM telemetry_points WHERE segment_id=? ORDER BY idx",
                       con(), params=(segment_id,))


def segment_features(segment_id: int) -> dict | None:
    r = con().execute("SELECT json FROM features WHERE segment_id=?", (segment_id,)).fetchone()
    if r is None:
        return None
    return {"features": json.loads(r["json"]), "published_18": PUBLISHED_18, "extras": EXTRA_NAMES}


def channel_telemetry(ch: str, start, end, max_points: int) -> dict | None:
    if ch not in CHANNELS:
        return None
    q = "SELECT segment_id, timestamp, value FROM telemetry_points WHERE channel=?"
    params = [ch]
    if start:
        q += " AND timestamp>=?"; params.append(start)
    if end:
        q += " AND timestamp<=?"; params.append(end)
    df = pd.read_sql(q + " ORDER BY timestamp", con(), params=params)
    segs = (df.groupby("segment_id")["timestamp"].agg(["first", "last"]).reset_index()
            .rename(columns={"first": "start", "last": "end"}))
    split = dict(con().execute("SELECT segment_id, split FROM segments WHERE channel=?", (ch,)).fetchall())
    if len(df) > max_points:
        df = df.iloc[np.linspace(0, len(df) - 1, max_points).astype(int)]
    downsampled = len(df) > max_points
    out = _series(df.reset_index(drop=True), None, 1)
    if downsampled:   # gaps between DOWNSAMPLED points are an artefact, not a property of the telemetry
        out["gaps"] = []
    out["segments"] = [{"segment_id": int(s.segment_id), "start": s.start, "end": s.end,
                        "split": split.get(int(s.segment_id))} for s in segs.itertuples()]
    out["downsampled"] = bool(len(out["t"]) == max_points)
    return out


def list_segments(split, sort, limit, status) -> list[dict]:
    q = ("SELECT s.segment_id, s.channel, s.channel_name, s.channel_kind, s.split, s.sampling, "
         "s.n_points, s.start, s.end, p.probability, p.decision, "
         "COALESCE(i.review_status, 'unreviewed') review_status "
         "FROM segments s LEFT JOIN predictions p USING(segment_id) "
         "LEFT JOIN (SELECT segment_id, review_status FROM investigations GROUP BY segment_id) i USING(segment_id)")
    where, params = [], []
    if split:
        where.append("s.split=?"); params.append(split)
    if status:
        where.append("COALESCE(i.review_status,'unreviewed')=?"); params.append(status)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY p.probability DESC" if sort == "probability" else " ORDER BY s.segment_id"
    q += " LIMIT ?"; params.append(limit)
    return [dict(r) | {"label": None} for r in con().execute(q, params).fetchall()]


def documents() -> list[dict]:
    return [dict(r) for r in con().execute(
        "SELECT doc_id, title, url, license, category, stored_mode, publication_date, retrieved_at, n_chunks "
        "FROM documents ORDER BY category, doc_id").fetchall()]


def document(doc_id: str) -> dict | None:
    d = con().execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
    if d is None:
        return None
    chunks = [dict(r) for r in con().execute("SELECT chunk_id, location, text FROM chunks WHERE doc_id=? ORDER BY ord",
                                             (doc_id,)).fetchall()]
    return {"document": dict(d), "chunks": chunks}
