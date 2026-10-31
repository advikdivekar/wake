"""segment -> features -> P(anomalous) -> decision -> top contributing measured characteristics."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from app.common.config import load_config
from app.common.paths import DATA_PROCESSED, EVAL_DIR, ROOT
from app.memory.db import connect
from app.telemetry.features import extra_features, published_features

PLAIN = {
    "gaps_squared": "Sum of squared time steps between samples (large when the signal has gaps)",
    "max_gap_s": "Longest gap between consecutive samples",
    "gap_count": "Number of sampling gaps",
    "zero_fraction": "Share of samples that are exactly zero",
    "max_zero_run": "Longest run of exact-zero samples",
    "n_zero_runs": "Number of runs of exact zeros",
    "n_peaks": "Number of prominent peaks",
    "smooth10_n_peaks": "Peaks after 10-point smoothing",
    "smooth20_n_peaks": "Peaks after 20-point smoothing",
    "diff_peaks": "Peaks in the first difference (sudden jumps)",
    "diff2_peaks": "Peaks in the second difference",
    "diff_var": "Variance of sample-to-sample changes",
    "diff2_var": "Variance of the second difference",
    "var": "Signal variance", "std": "Signal standard deviation", "mean": "Signal mean",
    "kurtosis": "Tailedness of the value distribution", "skew": "Asymmetry of the value distribution",
    "len": "Number of samples", "duration": "Segment duration (s, published definition)",
    "duration_total_s": "Segment duration (s)", "len_weighted": "Samples x sampling period",
    "var_div_duration": "Variance per second", "var_div_len": "Variance per sample",
    "dt_cv": "Irregularity of the sampling interval", "autocorr_lag1": "Lag-1 autocorrelation (smoothness)",
    "autocorr_lag10": "Lag-10 autocorrelation (slow structure)", "mad": "Median absolute deviation",
    "iqr": "Interquartile range", "q05": "5th percentile", "q95": "95th percentile", "range": "Value range",
    "max_abs_diff_norm": "Largest single jump relative to range",
}


@lru_cache
def classifier():
    from app.prediction.base import PickledClassifier
    return PickledClassifier(ROOT / load_config()["tabular_classifier"]["path"])


@lru_cache
def _train_stats():
    df = pd.read_csv(DATA_PROCESSED / "features.csv")
    tr = df[df.train == 1].replace([np.inf, -np.inf], np.nan)
    return tr


@lru_cache
def _importance() -> dict:
    p = EVAL_DIR / "feature_importance.json"
    return {d["feature"]: d["importance"] for d in json.loads(p.read_text())["features"]} if p.exists() else {}


def thresholds() -> dict:
    t = load_config()["thresholds"]
    return {"high": t["high"], "low": t["low"]}


def decide(p: float) -> str:
    t = thresholds()
    return "prioritise" if p >= t["high"] else "queue" if p >= t["low"] else "archive"


def contributors(feats: dict, k: int = 5) -> list[dict]:
    tr = _train_stats()
    imp = _importance()
    out = []
    for f, w in imp.items():
        if f not in feats or f not in tr:
            continue
        col = tr[f].astype(float)
        med, iqr = col.median(), (col.quantile(0.75) - col.quantile(0.25)) or (col.std() or 1.0)
        v = float(feats[f]) if feats[f] is not None and np.isfinite(feats[f]) else float("nan")
        z = 0.0 if np.isnan(v) else (v - med) / iqr
        out.append({"feature": f, "value": v, "z": round(float(z), 2), "importance": round(w, 4),
                    "plain": PLAIN.get(f, f), "_score": max(w, 0) * min(abs(z), 10)})
    out.sort(key=lambda d: -d["_score"])
    return [{k_: v_ for k_, v_ in d.items() if k_ != "_score"} for d in out[:k]]


def features_for_segment(segment_id: int) -> dict:
    r = connect().execute("SELECT json FROM features WHERE segment_id=?", (segment_id,)).fetchone()
    return json.loads(r["json"]) if r else {}


def predict_segment(segment_id: int) -> dict | None:
    con = connect()
    r = con.execute("SELECT * FROM predictions WHERE segment_id=?", (segment_id,)).fetchone()
    if r is None:
        return None
    feats = features_for_segment(segment_id)
    return {"segment_id": segment_id, "probability": round(r["probability"], 4), "decision": decide(r["probability"]),
            "thresholds": thresholds(), "model": r["model"], "source": r["source"],
            "contributors": contributors(feats)}


def predict_raw(channel: str, sampling: int, t: list[str], v: list[float]) -> dict:
    ts = pd.Series(pd.to_datetime(t))
    vals = np.asarray(v, dtype=float)
    feats = {**published_features(ts, vals, sampling), **extra_features(ts, vals, sampling, channel), "sampling": sampling}
    clf = classifier()
    x = np.array([[feats.get(f, np.nan) if np.isfinite(feats.get(f, np.nan)) else np.nan for f in clf.features]])
    p = float(clf.predict_proba(x)[0])
    return {"segment_id": None, "probability": round(p, 4), "decision": decide(p), "thresholds": thresholds(),
            "model": clf.name, "source": "computed on submitted signal", "contributors": contributors(feats)}
