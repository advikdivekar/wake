"""Export real, traceable numbers for the static landing site (site/data.js).

Nothing on the site is hand-typed: every metric, count, date and telemetry trace
comes from evaluations/*, data/documents/timeline.yaml and data/processed/mission.db.
Run:  .venv/bin/python -m scripts.build_site_data
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evaluations"
OUT = ROOT / "site" / "data.js"


def load(name):
    p = EV / name
    return json.loads(p.read_text()) if p.exists() else None


def short(m: str) -> str:
    base = m.split(":")[0]
    return {"tabpfn-v2": "TabPFN-v2", "rf": "Random Forest", "xgboost": "XGBoost", "lightgbm": "LightGBM",
            "lr": "Logistic Reg.", "iforest": "Isolation Forest", "rule": "Zero-fraction rule"}.get(base, base)


def metrics(m):
    return {k: round(float(m[k]), 4) for k in ("auprc", "auroc", "f1", "precision", "recall", "mcc") if k in m}


def published():
    """Parse the published rows out of ours_vs_published.md (already cited there)."""
    rows = []
    p = EV / "ours_vs_published.md"
    if not p.exists():
        return rows
    for line in p.read_text().splitlines():
        if line.startswith("| ") and "(published" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            name = cells[0].split("(")[0].strip()
            vals = [float(c) for c in cells[1:7]]
            rows.append({"model": name, **dict(zip(["auprc", "auroc", "f1", "precision", "recall", "mcc"], vals))})
    return rows


def predictions():
    p = ROOT / "data/processed/test_stages/test_tabpfn.csv"
    out = {}
    if p.exists():
        with p.open() as f:
            r = csv.reader(f)
            next(r)
            for seg, prob in r:
                out[int(seg)] = float(prob)
    return out


def traces(con, probs):
    """Pick a few real test segments: two anomalies the model caught, one nominal, one miss."""
    cur = con.cursor()
    rows = cur.execute("SELECT segment_id, channel, channel_name, channel_kind, start, end, label, n_points "
                       "FROM segments WHERE split='test'").fetchall()
    ok = lambda r: 120 <= r[7] <= 400
    tp = sorted([r for r in rows if ok(r) and r[6] == 1 and probs.get(r[0], 0) > 0.9], key=lambda r: -probs[r[0]])
    tn = sorted([r for r in rows if ok(r) and r[6] == 0 and r[0] in probs], key=lambda r: probs[r[0]])
    fn = [r for r in rows if r[6] == 1 and r[0] in probs and probs[r[0]] < 0.6168]
    picks = []
    for group, case in ((tp[:1], "TP"), (tp[5:6], "TP"), (tn[:1], "TN"), (fn[:1], "FN")):
        for r in group:
            vals = [v for (v,) in cur.execute(
                "SELECT value FROM telemetry_points WHERE segment_id=? ORDER BY idx", (r[0],))]
            step = max(1, len(vals) // 400)
            vals = vals[::step]
            picks.append({"segment_id": r[0], "channel": r[1], "channel_name": r[2], "kind": r[3],
                          "start": r[4], "end": r[5], "label": r[6], "case": case,
                          "probability": round(probs[r[0]], 4), "v": vals})
    return picks


def main():
    tab = load("tabpfn_test_results.json") or {"models": []}
    base = load("baselines_test_results.json") or {"models": []}
    ver = load("dataset_verification.json") or {}
    thr = load("thresholds.json")
    ours = [{"model": short(m["model"]), "id": m["model"], **metrics(m),
             "confusion": m.get("confusion")} for m in tab["models"] + base["models"]]

    tl = yaml.safe_load((ROOT / "data/documents/timeline.yaml").read_text())
    timeline = [{"date": e["date"], "date_kind": e["date_kind"], "approx": e.get("approx"), "title": e["title"],
                 "source": (e.get("citation") or {}).get("title"), "url": (e.get("citation") or {}).get("url"),
                 "excerpt": (e.get("citation") or {}).get("excerpt"), "measured": e.get("measured")} for e in tl]

    con = sqlite3.connect(ROOT / "data/processed/mission.db")
    ch = con.execute("SELECT channel, channel_name, channel_kind, COUNT(*), "
                     "AVG(CASE WHEN split='train' THEN label END) FROM segments GROUP BY channel").fetchall()
    channels = [{"channel": c, "name": n, "kind": k, "segments": s, "anomaly_rate_train": round(a or 0, 4)}
                for c, n, k, s, a in ch]
    split = dict(con.execute("SELECT split, COUNT(*) FROM segments GROUP BY split").fetchall())
    n_docs = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    n_chunks = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    n_points = con.execute("SELECT COUNT(*) FROM telemetry_points").fetchone()[0]
    anomaly_rate = con.execute("SELECT AVG(label) FROM segments").fetchone()[0]

    data = {
        "source": {"git_sha": tab.get("git_sha"), "produced_by": "python -m scripts.build_site_data"},
        "dataset": {"segments": sum(split.values()), "train": split.get("train"), "test": split.get("test"),
                    "channels": len(channels), "points": n_points, "anomaly_rate": round(anomaly_rate, 4),
                    "time_range": (ver.get("segments_csv") or {}).get("time_range"),
                    "md5_ok": all(v.get("ok") for v in (ver.get("checksums") or {}).values()) if ver else None,
                    "doi": "10.5281/zenodo.12588359", "license": "CC-BY-4.0"},
        "archive": {"documents": n_docs, "chunks": n_chunks},
        "thresholds": thr,
        "ours": ours,
        "published": published(),
        "channels": channels,
        "timeline": timeline,
        "significance": [{"baseline": short(t["baseline"]), "mcnemar_p": t["mcnemar"]["exact_mcnemar_p"],
                          "auprc_diff_ci95": t["auprc_diff_ci95"]}
                         for t in (load("significance_tests.json") or {"tests": []})["tests"]],
        "traces": traces(con, predictions()),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("// generated by scripts/build_site_data.py, do not edit\nwindow.SITE_DATA = "
                   + json.dumps(data, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.1f} KB): {len(ours)} models, {len(timeline)} timeline, "
          f"{len(data['traces'])} traces")


if __name__ == "__main__":
    main()
