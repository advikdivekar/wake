"""Cross-validated model selection on the OPSSAT-AD TRAINING split only.

Steps (all 5-fold StratifiedGroupKFold on train==1):
  1. TabPFN-v2 (n=4) on base18, then base18 + each extra-feature group (ablation).
  2. Keep groups that improve mean CV AUPRC; evaluate the combined set.
  3. Sweep n_estimators {4, 8, 16} (and gated versions if HF_TOKEN is set) on the selected set.
  4. Baselines on identical folds, on base18 and on the selected set.
  5. Save out-of-fold probabilities (for thresholds/calibration) + permutation importance.
Outputs: evaluations/tabpfn_cv_results.csv, baselines_cv_results.csv, tabpfn_selection.json,
         data/processed/oof_<model>.csv, evaluations/feature_importance.json
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from app.common.paths import DATA_PROCESSED, EVAL_DIR, write_eval_json
from training.tabpfn.common import (EXTRA_GROUPS, ZeroFractionRule, cv_groups, feature_list, load_frame,
                                    make_baseline, make_tabpfn, metrics, splitter, tabpfn_versions)

CMD = "python -m training.tabpfn.train"


def run_cv(name, factory, X: pd.DataFrame, y: np.ndarray, groups, as_frame=False):
    oof = np.zeros(len(y))
    rows = []
    for fold, (a, b) in enumerate(splitter().split(X, y, groups)):
        t = time.time()
        m = factory()
        Xa, Xb = (X.iloc[a], X.iloc[b]) if as_frame else (X.iloc[a].to_numpy(), X.iloc[b].to_numpy())
        m.fit(Xa, y[a])
        p = m.predict_proba(Xb)[:, 1]
        oof[b] = p
        r = metrics(y[b], p)
        rows.append({"variant": name, "fold": fold, **{k: v for k, v in r.items() if k != "confusion"},
                     "seconds": round(time.time() - t, 1)})
    summary = metrics(y, oof)
    print(f"{name:45s} AUPRC {np.mean([r['auprc'] for r in rows]):.4f} F1 {np.mean([r['f1'] for r in rows]):.4f}"
          f"  ({sum(r['seconds'] for r in rows):.0f}s)", flush=True)
    return rows, oof, summary


def mean_auprc(rows):
    return float(np.mean([r["auprc"] for r in rows]))


STAGE_DIR = DATA_PROCESSED / "cv_stages"
STAGE_DIR.mkdir(exist_ok=True)


def stage_tabpfn():
    df = load_frame()
    tr = df[df.train == 1].reset_index(drop=True)
    y = tr["anomaly"].to_numpy(); g = cv_groups(tr)
    tab_rows, oofs, selection = [], {}, {"ablation": {}}
    base_cols = feature_list([])
    r, _, _ = run_cv("tabpfn-v2:n4:base18", lambda: make_tabpfn("v2", 4), tr[base_cols], y, g)
    tab_rows += r; ref = mean_auprc(r); selection["ablation"]["base18"] = ref
    kept = []
    for grp in EXTRA_GROUPS:
        cols = feature_list([grp])
        r, _, _ = run_cv(f"tabpfn-v2:n4:base18+{grp}", lambda: make_tabpfn("v2", 4), tr[cols], y, g)
        tab_rows += r; s_ = mean_auprc(r); selection["ablation"][grp] = s_
        if s_ > ref + 0.001:
            kept.append(grp)
    if len(kept) > 1:
        cols = feature_list(kept)
        r, _, _ = run_cv(f"tabpfn-v2:n4:base18+{'+'.join(kept)}", lambda: make_tabpfn("v2", 4), tr[cols], y, g)
        tab_rows += r; s_ = mean_auprc(r); selection["ablation"]["combined"] = s_
        if s_ <= max(selection["ablation"][k] for k in kept):   # combination not better than best single group
            kept = [max(kept, key=lambda k: selection["ablation"][k])]
    selected_cols = feature_list(kept)
    fset = "base18" + ("+" + "+".join(kept) if kept else "")
    selection.update({"kept_groups": kept, "feature_set": fset, "features": selected_cols,
                      "rule": "keep a group if CV AUPRC improves by >0.001 over base18; keep the combination "
                              "only if it beats the best single kept group"})
    best = None
    for ver in tabpfn_versions():
        for n in (4, 8, 16):
            name = f"tabpfn-{ver}:n{n}:{fset}"
            r, oof, _ = run_cv(name, lambda: make_tabpfn(ver, n), tr[selected_cols], y, g)
            tab_rows += r; oofs[name] = oof
            s_ = mean_auprc(r)
            if best is None or s_ > best[1] + 1e-4:
                best = (name, s_, ver, n)
    selection["final"] = {"name": best[0], "cv_auprc": best[1], "version": best[2], "n_estimators": best[3]}
    pd.DataFrame(tab_rows).to_csv(EVAL_DIR / "tabpfn_cv_results.csv", index=False)
    pd.DataFrame({"segment": tr["segment"], **oofs}).to_csv(STAGE_DIR / "oof_tabpfn.csv", index=False)
    (STAGE_DIR / "selection_tabpfn.json").write_text(json.dumps(selection))

    # permutation importance (fold 0 of train CV, selected config, n=4)
    from sklearn.metrics import average_precision_score
    a, bidx = next(splitter().split(tr, y, g))
    m = make_tabpfn(best[2], 4).fit(tr[selected_cols].iloc[a].to_numpy(), y[a])
    Xb = tr[selected_cols].iloc[bidx].to_numpy(); yb = y[bidx]
    base_s = average_precision_score(yb, m.predict_proba(Xb)[:, 1])
    rng = np.random.default_rng(0); imp = []
    for j, c in enumerate(selected_cols):
        drops = []
        for _ in range(3):
            Xp = Xb.copy(); Xp[:, j] = rng.permutation(Xp[:, j])
            drops.append(base_s - average_precision_score(yb, m.predict_proba(Xp)[:, 1]))
        imp.append({"feature": c, "importance": float(np.mean(drops)), "std": float(np.std(drops))})
    imp.sort(key=lambda d: -d["importance"])
    write_eval_json("feature_importance.json", {
        "method": "permutation importance (AUPRC drop), 3 repeats, held-out fold 0 of training CV, "
                  f"TabPFN-{best[2]} n=4 on {fset}", "baseline_auprc": base_s, "features": imp}, CMD)


def stage_baselines():
    sel = json.loads((STAGE_DIR / "selection_tabpfn.json").read_text())
    df = load_frame()
    tr = df[df.train == 1].reset_index(drop=True)
    y = tr["anomaly"].to_numpy(); g = cv_groups(tr)
    base_rows, oofs = [], {}
    sets = [("base18", feature_list([]))]
    if sel["feature_set"] != "base18":
        sets.append((sel["feature_set"], sel["features"]))
    for cols_name, cols in sets:
        for b in ("lr", "rf", "xgboost", "lightgbm", "iforest"):
            name = f"{b}:{cols_name}"
            r, oof, _ = run_cv(name, lambda: make_baseline(b), tr[cols], y, g)
            base_rows += r; oofs[name] = oof
    r, oof, _ = run_cv("rule:zero_fraction", ZeroFractionRule, tr, y, g, as_frame=True)
    base_rows += r; oofs["rule:zero_fraction"] = oof
    pd.DataFrame(base_rows).to_csv(EVAL_DIR / "baselines_cv_results.csv", index=False)
    pd.DataFrame({"segment": tr["segment"], **oofs}).to_csv(STAGE_DIR / "oof_baselines.csv", index=False)


def stage_merge():
    sel = json.loads((STAGE_DIR / "selection_tabpfn.json").read_text())
    df = load_frame(); tr = df[df.train == 1].reset_index(drop=True)
    a = pd.read_csv(STAGE_DIR / "oof_tabpfn.csv"); b = pd.read_csv(STAGE_DIR / "oof_baselines.csv")
    oof = tr[["segment", "anomaly"]].merge(a, on="segment").merge(b, on="segment")
    oof.to_csv(DATA_PROCESSED / "oof_predictions.csv", index=False)
    bdf = pd.read_csv(EVAL_DIR / "baselines_cv_results.csv").groupby("variant")["auprc"].mean()
    fams = {}
    for v, s_ in bdf.items():
        fam = v.split(":")[0]
        if fam not in fams or s_ > fams[fam][1]:
            fams[fam] = (v, float(s_))
    sel["baselines_final"] = {k: {"name": v[0], "cv_auprc": v[1]} for k, v in fams.items()}
    write_eval_json("tabpfn_selection.json", sel, CMD)
    print(json.dumps(sel["final"]), json.dumps(sel["baselines_final"]), flush=True)


def main():
    import subprocess
    import sys
    for st in ("tabpfn", "baselines", "merge"):
        subprocess.run([sys.executable, "-m", "training.tabpfn.train", "--stage", st], check=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["tabpfn", "baselines", "merge"])
    st = ap.parse_args().stage
    {"tabpfn": stage_tabpfn, "baselines": stage_baselines, "merge": stage_merge, None: main}[st]()
