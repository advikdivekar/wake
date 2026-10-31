"""Fill README.md and post/DEV_POST.md from templates using ONLY numbers in /evaluations.

Templates use {{key}} placeholders, where key names a value from the `numbers()` table below. Every value
records the evaluation file it came from (evaluations/post_numbers.json). Missing values render as
"[not yet measured]", and --check fails if any placeholder is unresolved.
Usage: python -m scripts.fill_post [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evaluations"
MISSING = "[not yet measured]"


def _j(name):
    p = EV / name
    return json.loads(p.read_text()) if p.exists() else None


def numbers() -> dict[str, tuple[str, str]]:
    N: dict[str, tuple[str, str]] = {}

    def put(k, v, src, fmt="{:.3f}"):
        if v is not None:
            N[k] = (fmt.format(v) if isinstance(v, float) else str(v), src)

    dv = _j("dataset_verification.json")
    if dv:
        put("data.segments", dv["segments_csv"]["n_segments"], "dataset_verification.json")
        put("data.points", f"{dv['segments_csv']['rows']:,}", "dataset_verification.json")
        put("data.train", dv["split"]["train"], "dataset_verification.json")
        put("data.test", dv["split"]["test"], "dataset_verification.json")
        put("data.anomaly_rate", dv["anomaly_rate"] * 100, "dataset_verification.json", "{:.1f}%")
    fr = _j("feature_reproduction.json")
    if fr:
        put("feat.overall", fr["overall_pct_within_tol"] * 100, "feature_reproduction.json", "{:.2f}%")
        put("feat.exact_count", sum(1 for v in fr["features"].values() if v["pct_within_tol"] == 1.0), "feature_reproduction.json")
    sel = _j("tabpfn_selection.json")
    if sel:
        put("tab.cv_auprc", sel["final"]["cv_auprc"], "tabpfn_selection.json", "{:.4f}")
        put("tab.config", sel["final"]["name"], "tabpfn_selection.json")
    tr = _j("tabpfn_test_results.json")
    if tr:
        m = tr["models"][0]
        for k in ("auprc", "auroc", "f1", "precision", "recall", "mcc", "brier"):
            put(f"tab.{k}", m[k], "tabpfn_test_results.json")
        put("tab.auprc_ci", f"{m['ci']['auprc'][0]:.3f}–{m['ci']['auprc'][1]:.3f}", "tabpfn_test_results.json")
        put("tab.f1_ci", f"{m['ci']['f1'][0]:.3f}–{m['ci']['f1'][1]:.3f}", "tabpfn_test_results.json")
        (tn, fp), (fn, tp) = m["confusion"]
        put("tab.fp", fp, "tabpfn_test_results.json"); put("tab.fn", fn, "tabpfn_test_results.json")
        put("tab.tp", tp, "tabpfn_test_results.json"); put("tab.tn", tn, "tabpfn_test_results.json")
        put("tab.threshold", m["threshold"], "tabpfn_test_results.json")
    bl = _j("baselines_test_results.json")
    if bl:
        for m in bl["models"]:
            fam = m["model"].split(":")[0]
            put(f"base.{fam}.auprc", m["auprc"], "baselines_test_results.json")
            put(f"base.{fam}.f1", m["f1"], "baselines_test_results.json")
            put(f"base.{fam}.mcc", m["mcc"], "baselines_test_results.json")
    sig = _j("significance_tests.json")
    if sig:
        for t in sig["tests"]:
            fam = t["baseline"].split(":")[0]
            put(f"sig.{fam}.p", t["mcnemar"]["exact_mcnemar_p"], "significance_tests.json", "{:.3g}")
            put(f"sig.{fam}.diff", t["auprc_diff_mean"], "significance_tests.json", "{:+.4f}")
    ab = _j("ablation_base18_test.json")
    if ab:
        for m in ab["models"]:
            fam = m["model"].split(":")[0]
            put(f"abl.{fam}.auprc", m["auprc"], "ablation_base18_test.json")
            put(f"abl.{fam}.f1", m["f1"], "ablation_base18_test.json")
            put(f"abl.{fam}.mcc", m["mcc"], "ablation_base18_test.json")
    th = _j("thresholds.json")
    if th:
        put("thr.high", th["high"], "thresholds.json", "{:.2f}"); put("thr.low", th["low"], "thresholds.json", "{:.2f}")
    st = _j("sft_dataset_stats.json")
    if st:
        for sp in ("train", "val", "test"):
            put(f"sft.{sp}", st[sp]["total"], "sft_dataset_stats.json")
            put(f"sft.{sp}.A", st[sp]["task_A"], "sft_dataset_stats.json")
    for task in "ABCD":
        e = _j(f"tinker_eval_{task}.json")
        if not e:
            continue
        key = {"A": "field_exact_match", "B": "both_correct", "C": "overall", "D": "all_checks"}[task]
        put(f"tk.{task}.base", e["base"][key], f"tinker_eval_{task}.json")
        put(f"tk.{task}.tuned", e["tuned"][key], f"tinker_eval_{task}.json")
        put(f"tk.{task}.p", e["paired"]["exact_p"], f"tinker_eval_{task}.json", "{:.3g}")
        put(f"tk.{task}.tuned_ci", "–".join(f"{x:.3f}" for x in e["tuned"]["wilson95"]), f"tinker_eval_{task}.json")
        if task == "A":
            for k in ("valid_schema_rate", "evidence_fidelity", "unsupported_root_causes", "record_exact_match",
                      "null_correctness", "validator_caught_errors", "field_exact_match_after_validator"):
                put(f"tk.A.base.{k}", e["base"][k], "tinker_eval_A.json")
                put(f"tk.A.tuned.{k}", e["tuned"][k], "tinker_eval_A.json")
    cost = _j("tinker_cost.json")
    if cost:
        put("tk.cost_total", cost.get("total_est_usd"), "tinker_cost.json", "${:.2f}")
    off = _j("offline_inference.json")
    if off:
        put("off.em", off["task_A"]["field_exact_match"], "offline_inference.json")
        put("off.agree", off.get("field_agreement_with_tinker_bf16_outputs"), "offline_inference.json")
        put("off.sec", off["seconds_per_passage"], "offline_inference.json", "{:.1f}")
    lc = _j("tinker_learning_curve.json")
    if lc:
        for row in lc["points"]:
            put(f"lc.{row['n_examples']}", row["val_exact_match"], "tinker_learning_curve.json")
            if row["run"] == "final-v2":
                put("lc.final", row["val_exact_match"], "tinker_learning_curve.json")
            if row["run"] == "offline-n200-v2":
                put("lc.offline", row["val_exact_match"], "tinker_learning_curve.json")
    return N


def fill(template: str, N: dict) -> tuple[str, list[str]]:
    missing = []

    def rep(m):
        k = m.group(1).strip()
        if k in N:
            return N[k][0]
        missing.append(k)
        return MISSING
    return re.sub(r"\{\{([^}]+)\}\}", rep, template), missing


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    N = numbers()
    (EV / "post_numbers.json").write_text(json.dumps({k: {"value": v, "source": s} for k, (v, s) in N.items()}, indent=1))
    all_missing = {}
    for tpl, out in ((ROOT / "docs" / "README.template.md", ROOT / "README.md"),
                     (ROOT / "post" / "DEV_POST.template.md", ROOT / "post" / "DEV_POST.md")):
        if tpl.exists():
            text, miss = fill(tpl.read_text(), N)
            out.write_text(text)
            all_missing[out.name] = sorted(set(miss))
    print(json.dumps(all_missing, indent=1))
    if a.check and any(all_missing.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
