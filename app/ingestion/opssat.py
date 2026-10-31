"""Download + verify OPSSAT-AD and compute/verify features.

Usage: python -m app.ingestion.opssat [--download] [--features]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request

import numpy as np
import pandas as pd

from app.common.channels import CHANNELS
from app.common.paths import DATA_PROCESSED, DATA_RAW, write_eval_json
from app.telemetry.features import PUBLISHED_18, compute_all

ZENODO = "https://zenodo.org/records/12588359/files/{name}?download=1"
EXPECTED_MD5 = {
    "segments.csv": "1f4b6ffd0359efac96a6698ff557e0f9",
    "dataset.csv": "c12fb83863afa4463dec07303a20bb14",
}


def md5(path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download() -> None:
    for name in EXPECTED_MD5:
        dest = DATA_RAW / name
        if not dest.exists():
            print(f"downloading {name} ...")
            urllib.request.urlretrieve(ZENODO.format(name=name), dest)


def load_segments() -> pd.DataFrame:
    df = pd.read_csv(DATA_RAW / "segments.csv", parse_dates=["timestamp"])
    return df


def load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATA_RAW / "dataset.csv")


def verify() -> dict:
    seg = load_segments()
    ds = load_dataset()
    per_seg = seg.groupby("segment").agg(
        channel=("channel", "first"), anomaly=("anomaly", "first"), train=("train", "first"),
        sampling=("sampling", "first"), n=("value", "size"),
        n_channels=("channel", "nunique"), n_labels=("anomaly", "nunique"),
    )
    report = {
        "source": {"zenodo_record": "https://zenodo.org/records/12588359",
                   "doi": "10.5281/zenodo.12588359", "license": "CC-BY-4.0"},
        "checksums": {n: {"md5": md5(DATA_RAW / n), "expected": e, "ok": md5(DATA_RAW / n) == e}
                      for n, e in EXPECTED_MD5.items()},
        "segments_csv": {"rows": int(len(seg)), "columns": list(seg.columns),
                         "n_segments": int(seg.segment.nunique()),
                         "time_range": [str(seg.timestamp.min()), str(seg.timestamp.max())]},
        "dataset_csv": {"rows": int(len(ds)), "columns": list(ds.columns)},
        "channels": sorted(seg.channel.unique().tolist()),
        "channels_match_paper": sorted(seg.channel.unique().tolist()) == sorted(CHANNELS),
        "segment_integrity": {
            "single_channel_per_segment": bool((per_seg.n_channels == 1).all()),
            "single_label_per_segment": bool((per_seg.n_labels == 1).all()),
        },
        "split": {
            "train": int((per_seg.train == 1).sum()), "test": int((per_seg.train == 0).sum()),
            "train_anomalous": int(((per_seg.train == 1) & (per_seg.anomaly == 1)).sum()),
            "test_anomalous": int(((per_seg.train == 0) & (per_seg.anomaly == 1)).sum()),
        },
        "anomaly_rate": float(per_seg.anomaly.mean()),
        "sampling_values": {str(k): int(v) for k, v in per_seg.sampling.value_counts().items()},
        "per_channel": {
            ch: {"segments": int(len(g)), "anomalous": int(g.anomaly.sum()),
                 "train": int((g.train == 1).sum()), "test": int((g.train == 0).sum())}
            for ch, g in per_seg.groupby("channel")
        },
        "points_per_segment": {"min": int(per_seg.n.min()), "median": float(per_seg.n.median()),
                               "max": int(per_seg.n.max())},
        "expected_from_paper": {"segments": 2123, "train": 1494, "test": 529, "channels": 9,
                                "anomaly_rate_approx": 0.20},
    }
    write_eval_json("dataset_verification.json", report, "python -m app.ingestion.opssat --verify")
    return report


def features_and_reproduction() -> dict:
    seg = load_segments()
    feats = compute_all(seg)
    feats.to_parquet(DATA_PROCESSED / "features.parquet", index=False) if _has_pyarrow() else None
    feats.to_csv(DATA_PROCESSED / "features.csv", index=False)
    ref = load_dataset().set_index("segment").sort_index()
    ours = feats.set_index("segment").sort_index()
    out = {"n_segments_compared": int(len(ref)), "label_agreement": {}, "features": {}}
    for col in ["anomaly", "train", "channel", "sampling"]:
        out["label_agreement"][col] = float((ours.loc[ref.index, col] == ref[col]).mean())
    for f in PUBLISHED_18:
        a = ours.loc[ref.index, f].astype(float).to_numpy()
        b = ref[f].astype(float).to_numpy()
        both_inf = np.isinf(a) & np.isinf(b)
        close = np.isclose(a, b, rtol=1e-6, atol=1e-12, equal_nan=True) | both_inf
        finite = np.isfinite(a) & np.isfinite(b)
        rel = np.abs(a[finite] - b[finite]) / np.maximum(np.abs(b[finite]), 1e-30)
        out["features"][f] = {"pct_within_tol": float(close.mean()),
                              "max_rel_err": float(rel.max()) if rel.size else 0.0,
                              "n_mismatch": int((~close).sum())}
    out["overall_pct_within_tol"] = float(np.mean([v["pct_within_tol"] for v in out["features"].values()]))
    out["tolerance"] = {"rtol": 1e-6, "atol": 1e-12}
    write_eval_json("feature_reproduction.json", out, "python -m app.ingestion.opssat --features")
    return out


def _has_pyarrow() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--features", action="store_true")
    a = ap.parse_args()
    if a.download:
        download()
    if a.verify:
        r = verify()
        print({k: r[k] for k in ("checksums", "split", "anomaly_rate", "channels_match_paper")})
    if a.features:
        r = features_and_reproduction()
        print("overall:", r["overall_pct_within_tol"])
        bad = {k: v for k, v in r["features"].items() if v["pct_within_tol"] < 1}
        print("imperfect:", bad, file=sys.stderr)
