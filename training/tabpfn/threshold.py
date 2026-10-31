"""Choose decision thresholds from TRAINING out-of-fold predictions only.

- t_f1   : maximises F1 on OOF (used for the headline binary metrics)
- t_high : smallest threshold with OOF precision >= 0.95 ("prioritise")
- t_low  : largest threshold with OOF recall >= 0.98 ("queue"); below -> "archive"
Writes threshold_tradeoff.csv, pr_curve.json (OOF), calibration.json (OOF) and updates config.yaml.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import yaml
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, precision_recall_curve

from app.common.paths import DATA_PROCESSED, EVAL_DIR, ROOT, write_eval_json

CMD = "python -m training.tabpfn.threshold"


def best_f1_threshold(y, p) -> float:
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec[:-1] * rec[:-1] / np.maximum(prec[:-1] + rec[:-1], 1e-12)
    return float(thr[int(np.argmax(f1))])


def tradeoff(y, p, grid) -> pd.DataFrame:
    rows = []
    for t in grid:
        yhat = p >= t
        tp = int((yhat & (y == 1)).sum()); fp = int((yhat & (y == 0)).sum()); fn = int((~yhat & (y == 1)).sum())
        rows.append({"threshold": round(float(t), 4), "missed_anomalies": fn, "false_alerts": fp,
                     "flagged": int(yhat.sum()), "precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1)})
    return pd.DataFrame(rows)


def main():
    sel = json.loads((EVAL_DIR / "tabpfn_selection.json").read_text())
    name = sel["final"]["name"]
    oof = pd.read_csv(DATA_PROCESSED / "oof_predictions.csv")
    y, p = oof["anomaly"].to_numpy(), oof[name].to_numpy()
    t_f1 = best_f1_threshold(y, p)
    grid = np.unique(np.r_[np.linspace(0.05, 0.95, 19), t_f1])
    tt = tradeoff(y, p, grid)
    hi = tt[tt.precision >= 0.95]
    t_high = float(hi.threshold.min()) if len(hi) else float(t_f1)
    lo = tt[tt.recall >= 0.98]
    t_low = float(lo.threshold.max()) if len(lo) else 0.1
    t_low = min(t_low, t_high)
    tt["source"] = "training out-of-fold predictions (5-fold CV)"
    tt.to_csv(EVAL_DIR / "threshold_tradeoff.csv", index=False)

    curves = {}
    for col in [c for c in oof.columns if c not in ("segment", "anomaly")]:
        pr, rc, th = precision_recall_curve(y, oof[col])
        idx = np.unique(np.linspace(0, len(th) - 1, min(200, len(th))).astype(int))
        curves[col] = [{"threshold": float(th[i]), "precision": float(pr[i]), "recall": float(rc[i])} for i in idx]
    write_eval_json("pr_curve_oof.json", {"source": "training OOF", "curves": curves}, CMD)

    frac, mean = calibration_curve(y, p, n_bins=10, strategy="quantile")
    counts = np.histogram(p, bins=np.quantile(p, np.linspace(0, 1, 11)))[0]
    write_eval_json("calibration_oof.json", {
        "model": name, "source": "training OOF",
        "bins": [{"p_mean": float(m), "frac_pos": float(f), "count": int(c)} for m, f, c in zip(mean, frac, counts)],
        "brier": float(brier_score_loss(y, p))}, CMD)

    thresholds = {"f1": round(t_f1, 4), "high": round(t_high, 4), "low": round(t_low, 4),
                  "rule": "prioritise if p>=high (OOF precision>=0.95); queue if p>=low (OOF recall>=0.98); else archive"}
    write_eval_json("thresholds.json", {"model": name, **thresholds}, CMD)
    cfg_path = ROOT / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["thresholds"] = {"high": thresholds["high"], "low": thresholds["low"], "f1": thresholds["f1"]}
    text = cfg_path.read_text()
    import re
    text = re.sub(r"thresholds:.*?\nretrieval:", "thresholds:                    # from training/tabpfn/threshold.py (OOF)\n"
                  f"  high: {thresholds['high']}\n  low: {thresholds['low']}\n  f1: {thresholds['f1']}\nretrieval:",
                  text, flags=re.S)
    cfg_path.write_text(text)
    print(thresholds)


if __name__ == "__main__":
    main()
