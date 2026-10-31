"""Post-hoc, like-for-like ablation: every model on ONLY the 18 published features (the paper's setting).
NOT used for any selection decision (the final configuration was fixed by CV beforehand). Each config is
run on the test split once and logged by the same guard as evaluate.py.
Usage: python -m training.tabpfn.ablation   (spawns separate processes: torch vs tree libraries)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

import pandas as pd

from app.common.paths import DATA_PROCESSED, EVAL_DIR, write_eval_json
from training.tabpfn.common import feature_list, load_frame, make_baseline, make_tabpfn, metrics
from training.tabpfn.evaluate import bootstrap_ci, guard
from training.tabpfn.threshold import best_f1_threshold

OUT = DATA_PROCESSED / "test_stages" / "ablation_base18.csv"


def stage(kind: str):
    df = load_frame()
    tr, te = df[df.train == 1].reset_index(drop=True), df[df.train == 0].reset_index(drop=True)
    cols = feature_list([])
    preds = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame({"segment": te.segment})
    models = ({"tabpfn-v2:n8:base18": lambda: make_tabpfn("v2", 8)} if kind == "tabpfn" else
              {f"{b}:base18": (lambda b=b: make_baseline(b)) for b in ("lr", "rf", "xgboost", "lightgbm")})
    for name, fac in models.items():
        guard("ablation_base18", {"model": name, "features": cols}, False)
        m = fac().fit(tr[cols].to_numpy(), tr.anomaly.to_numpy())
        preds[name] = m.predict_proba(te[cols].to_numpy())[:, 1]
    preds.to_csv(OUT, index=False)


def report():
    df = load_frame(); te = df[df.train == 0].reset_index(drop=True)
    preds = te[["segment", "anomaly"]].merge(pd.read_csv(OUT), on="segment")
    oof = pd.read_csv(DATA_PROCESSED / "oof_predictions.csv")
    rows = []
    for c in [c for c in preds.columns if c not in ("segment", "anomaly")]:
        t = best_f1_threshold(oof["anomaly"].to_numpy(), oof[c].to_numpy()) if c in oof else 0.5
        y, p = preds["anomaly"].to_numpy(), preds[c].to_numpy()
        rows.append({"model": c, "threshold": t, "threshold_source": "max-F1 on training OOF" if c in oof else "0.5 (no OOF run)",
                     **metrics(y, p, t), "ci": bootstrap_ci(y, p, t, n=500)})
    write_eval_json("ablation_base18_test.json", {
        "note": "Post-hoc like-for-like comparison with the paper (18 published features only). Not used for selection.",
        "models": rows}, "python -m training.tabpfn.ablation")
    md = EVAL_DIR / "ours_vs_published.md"
    text = md.read_text().split("\n## Like-for-like")[0].rstrip() + "\n"
    text += ("\n## Like-for-like: only the 18 published features (post-hoc ablation, not used for selection)\n\n"
             "| Model | AUCPR | AUCROC | F1 | Precision | Recall | MCC |\n|---|---|---|---|---|---|---|\n")
    for r in rows:
        text += (f"| {r['model']} (ours) | {r['auprc']:.3f} [{r['ci']['auprc'][0]:.3f}-{r['ci']['auprc'][1]:.3f}] | "
                 f"{r['auroc']:.3f} | {r['f1']:.3f} | {r['precision']:.3f} | {r['recall']:.3f} | {r['mcc']:.3f} |\n")
    text += "| FCNN (published best, same 18 features) | 0.979 | 0.989 | 0.946 | 0.963 | 0.929 | 0.932 |\n"
    text += ("\nTabPFN threshold here is 0.5 (this exact config had no OOF run); tree/LR thresholds are max-F1 on their "
             "base18 training OOF predictions.\n")
    md.write_text(text)
    for r in rows:
        print(f"{r['model']:24s} AUPRC {r['auprc']:.4f} F1 {r['f1']:.4f} MCC {r['mcc']:.4f}  thr {r['threshold']:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", choices=["tabpfn", "trees", "report"])
    st = ap.parse_args().stage
    if st == "report":
        report()
    elif st:
        stage(st)
    else:
        for s in ("tabpfn", "trees", "report"):
            subprocess.run([sys.executable, "-m", "training.tabpfn.ablation", "--stage", s], check=True)
