"""ONE-TIME evaluation on the official OPSSAT-AD test split (train==0).

Guarded: each final configuration may be run against the test set once. Every run is logged to the
`eval_runs` table and evaluations/test_run_log.jsonl. Re-running the same config is refused unless
--force is given (and the forced re-run is logged as such).
Outputs: tabpfn_test_results.json, baselines_test_results.json, significance_tests.json, pr_curve.json,
         calibration.json, ours_vs_published.md, models/tabpfn_final.pkl, predictions table.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, precision_recall_curve

from app.common.paths import DATA_PROCESSED, EVAL_DIR, MODELS_DIR, git_sha, now_iso, write_eval_json
from app.memory.db import init_db
from training.tabpfn.common import (ZeroFractionRule, feature_list, load_frame, make_baseline, make_tabpfn,
                                    metrics)
from training.tabpfn.threshold import best_f1_threshold

CMD = "python -m training.tabpfn.evaluate"
LOG = EVAL_DIR / "test_run_log.jsonl"


def guard(kind: str, config: dict, force: bool) -> None:
    h = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
    con = init_db()
    prev = con.execute("SELECT at FROM eval_runs WHERE kind=? AND config_hash=?", (kind, h)).fetchone()
    if prev and not force:
        raise SystemExit(f"REFUSED: {kind} config {h} already evaluated on the test set at {prev['at']}. "
                         "The official split is sacred; use --force only with a logged reason.")
    con.execute("INSERT INTO eval_runs(kind, config_hash, config, git_sha, at) VALUES (?,?,?,?,?)",
                (kind, h, json.dumps(config), git_sha(), now_iso()))
    con.commit()
    with open(LOG, "a") as f:
        f.write(json.dumps({"kind": kind, "config_hash": h, "config": config, "git_sha": git_sha(),
                            "at": now_iso(), "forced": bool(prev)}) + "\n")


def bootstrap_ci(y, p, thr, n=1000, seed=0) -> dict:
    rng = np.random.default_rng(seed)
    keys = ["auprc", "auroc", "f1", "precision", "recall", "mcc"]
    samples = {k: [] for k in keys}
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():
            continue
        m = metrics(y[idx], p[idx], thr)
        for k in keys:
            samples[k].append(m[k])
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in samples.items()}


def mcnemar(y, a_hat, b_hat) -> dict:
    a_ok, b_ok = a_hat == y, b_hat == y
    b01 = int((a_ok & ~b_ok).sum()); b10 = int((~a_ok & b_ok).sum())
    p = binomtest(b01, b01 + b10, 0.5).pvalue if b01 + b10 else 1.0
    return {"a_correct_b_wrong": b01, "a_wrong_b_correct": b10, "exact_mcnemar_p": float(p)}


STAGE_DIR = DATA_PROCESSED / "test_stages"
STAGE_DIR.mkdir(exist_ok=True)


def _ctx():
    sel = json.loads((EVAL_DIR / "tabpfn_selection.json").read_text())
    oof = pd.read_csv(DATA_PROCESSED / "oof_predictions.csv")
    df = load_frame()
    tr, te = df[df.train == 1].reset_index(drop=True), df[df.train == 0].reset_index(drop=True)
    return sel, oof, tr, te


def stage_tabpfn(force):
    sel, oof, tr, te = _ctx()
    fin, cols = sel["final"], sel["features"]
    thr = best_f1_threshold(oof["anomaly"].to_numpy(), oof[fin["name"]].to_numpy())
    guard("tabpfn_final", {"model": fin["name"], "features": cols, "threshold_oof_f1": thr}, force)
    model = make_tabpfn(fin["version"], fin["n_estimators"]).fit(tr[cols].to_numpy(), tr.anomaly.to_numpy())
    p = model.predict_proba(te[cols].to_numpy())[:, 1]
    with open(MODELS_DIR / "tabpfn_final.pkl", "wb") as f:
        pickle.dump({"model": model, "features": cols, "name": fin["name"], "threshold_f1": thr}, f)
    pd.DataFrame({"segment": te.segment, fin["name"]: p}).to_csv(STAGE_DIR / "test_tabpfn.csv", index=False)


def stage_baselines(force):
    sel, oof, tr, te = _ctx()
    out = {"segment": te.segment}
    for fam, info in sel["baselines_final"].items():
        name = info["name"]
        guard("baseline_final", {"model": name}, force)
        if fam == "rule":
            p = ZeroFractionRule().predict_proba(te)[:, 1]
        else:
            bcols = feature_list([]) if name.endswith(":base18") else sel["features"]
            m = make_baseline(fam).fit(tr[bcols].to_numpy(), tr.anomaly.to_numpy())
            p = m.predict_proba(te[bcols].to_numpy())[:, 1]
        out[name] = p
    pd.DataFrame(out).to_csv(STAGE_DIR / "test_baselines.csv", index=False)


def stage_report():
    sel, oof, tr, te = _ctx()
    fin = sel["final"]
    yte = te.anomaly.to_numpy()
    preds = te[["segment"]].merge(pd.read_csv(STAGE_DIR / "test_tabpfn.csv"), on="segment") \
                           .merge(pd.read_csv(STAGE_DIR / "test_baselines.csv"), on="segment")
    yo = oof["anomaly"].to_numpy()
    results = {c: (preds[c].to_numpy(), best_f1_threshold(yo, oof[c].to_numpy()))
               for c in preds.columns if c != "segment"}
    p_tab, thr_f1 = results[fin["name"]]
    tab_out = {"model": fin["name"], "threshold": thr_f1, "threshold_source": "max-F1 on training OOF",
               **metrics(yte, p_tab, thr_f1), "at_0.5": metrics(yte, p_tab, 0.5),
               "ci": bootstrap_ci(yte, p_tab, thr_f1)}
    write_eval_json("tabpfn_test_results.json", {"split": "official test (train==0)", "n_test": int(len(yte)),
                                                 "models": [tab_out]}, CMD)
    base_out = [{"model": n, "threshold": t, "threshold_source": "max-F1 on training OOF",
                 **metrics(yte, p, t), "ci": bootstrap_ci(yte, p, t, n=500)}
                for n, (p, t) in results.items() if n != fin["name"]]
    write_eval_json("baselines_test_results.json", {"split": "official test (train==0)", "n_test": int(len(yte)),
                                                    "models": base_out}, CMD)
    from sklearn.metrics import average_precision_score
    rng = np.random.default_rng(1); sig = []
    for name, (p, t) in results.items():
        if name == fin["name"]:
            continue
        diffs = []
        for _ in range(1000):
            idx = rng.integers(0, len(yte), len(yte))
            if yte[idx].min() == yte[idx].max():
                continue
            diffs.append(average_precision_score(yte[idx], p_tab[idx]) - average_precision_score(yte[idx], p[idx]))
        sig.append({"tabpfn": fin["name"], "baseline": name,
                    "mcnemar": mcnemar(yte, (p_tab >= thr_f1).astype(int), (p >= t).astype(int)),
                    "auprc_diff_mean": float(np.mean(diffs)),
                    "auprc_diff_ci95": [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]})
    write_eval_json("significance_tests.json", {"tests": sig, "note": "exact McNemar on thresholded decisions; "
                    "paired bootstrap (1000x) of the AUPRC difference TabPFN minus baseline"}, CMD)
    curves = {}
    for name, (p, _) in results.items():
        pr, rc, th = precision_recall_curve(yte, p)
        idx = np.unique(np.linspace(0, len(th) - 1, min(200, len(th))).astype(int))
        curves[name] = [{"threshold": float(th[i]), "precision": float(pr[i]), "recall": float(rc[i])} for i in idx]
    write_eval_json("pr_curve.json", {"source": "official test split", "curves": curves}, CMD)
    frac, mean = calibration_curve(yte, p_tab, n_bins=10, strategy="quantile")
    write_eval_json("calibration.json", {"model": fin["name"], "source": "official test split",
                                         "bins": [{"p_mean": float(m), "frac_pos": float(f)} for m, f in zip(mean, frac)],
                                         "brier": float(brier_score_loss(yte, p_tab))}, CMD)
    con = init_db()
    thr = json.loads((EVAL_DIR / "thresholds.json").read_text())
    con.execute("DELETE FROM predictions")

    def decide(p):
        return "prioritise" if p >= thr["high"] else "queue" if p >= thr["low"] else "archive"
    rows = [(int(s), float(p), decide(p), fin["name"], "test: final model") for s, p in zip(preds.segment, p_tab)]
    o = oof.set_index("segment")[fin["name"]]
    rows += [(int(s), float(o[s]), decide(o[s]), fin["name"], "train: out-of-fold") for s in tr.segment]
    con.executemany("INSERT INTO predictions VALUES (?,?,?,?,?)", rows)
    con.commit()
    write_comparison(tab_out, base_out)
    print(json.dumps({k: round(tab_out[k], 4) for k in ("auprc", "auroc", "f1", "precision", "recall", "mcc")}))


def main(force=False):
    import subprocess
    import sys
    extra = ["--force"] if force else []
    for st in ("tabpfn", "baselines", "report"):
        subprocess.run([sys.executable, "-m", "training.tabpfn.evaluate", "--stage", st, *extra], check=True)


def write_comparison(tab, bases):
    pub = [("FCNN (published best supervised)", 0.979, 0.989, 0.946, 0.963, 0.929, 0.932),
           ("XGBOD (published)", 0.975, 0.992, 0.918, 0.944, 0.894, 0.897),
           ("RF+ICCS (published)", 0.963, 0.985, 0.883, 0.978, 0.805, 0.862),
           ("MO-GAAL (published best unsupervised)", 0.779, 0.865, 0.726, 0.985, 0.575, 0.710),
           ("IForest (published)", 0.347, 0.635, 0.295, 0.297, 0.292, 0.105)]
    lines = ["# Ours vs published (official OPSSAT-AD test split, 529 segments)", "",
             "Published numbers: Ruszczak et al., Sci Data 2025, Table 3 (see published_benchmark.md).",
             "Our numbers: produced by `python -m training.tabpfn.evaluate` (one guarded test run per config); "
             "thresholds chosen on training out-of-fold predictions.", "",
             "| Model | AUCPR | AUCROC | F1 | Precision | Recall | MCC |", "|---|---|---|---|---|---|---|"]
    for r in [tab] + bases:
        ci = r.get("ci", {})
        lines.append(f"| **{r['model']}** (ours) | {r['auprc']:.3f} [{ci['auprc'][0]:.3f}-{ci['auprc'][1]:.3f}] | "
                     f"{r['auroc']:.3f} | {r['f1']:.3f} [{ci['f1'][0]:.3f}-{ci['f1'][1]:.3f}] | {r['precision']:.3f} | "
                     f"{r['recall']:.3f} | {r['mcc']:.3f} |")
    for row in pub:
        lines.append("| " + row[0] + " | " + " | ".join(f"{v:.3f}" for v in row[1:]) + " |")
    lines += ["", "Brackets: 95% bootstrap CI over test segments. Published results have no CIs; "
              "differences within our CI should be read as ties."]
    (EVAL_DIR / "ours_vs_published.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stage", choices=["tabpfn", "baselines", "report"])
    a = ap.parse_args()
    if a.stage == "tabpfn":
        stage_tabpfn(a.force)
    elif a.stage == "baselines":
        stage_baselines(a.force)
    elif a.stage == "report":
        stage_report()
    else:
        main(a.force)
