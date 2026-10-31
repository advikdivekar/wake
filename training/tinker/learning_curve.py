"""Score each training run's final checkpoint on VAL (Tinker sampling, budget-guarded) -> tinker_learning_curve.json."""
from __future__ import annotations

import json

from app.common.paths import EVAL_DIR, write_eval_json
from training.tinker.evaluate import run, score


def main(names=None):
    runs = json.loads((EVAL_DIR / "tinker_runs.json").read_text())["runs"]
    cost = json.loads((EVAL_DIR / "tinker_cost.json").read_text())["jobs"]
    pts = []
    base_p = EVAL_DIR / "tinker_val_base_local.json"
    for r in sorted(runs, key=lambda r: r["n_examples"]):
        if names and r["name"] not in names:
            continue
        outs = run("tuned", "val", "tinker", tag=r["name"], tinker_path=r["checkpoints"][-1]["sampler_path"])
        res = score("val", outs)
        train_usd = sum(j["est_usd"] for j in cost if j["job"] == f"train:{r['name']}")
        pts.append({"run": r["name"], "n_examples": r["n_examples"], "epochs": r["epochs"],
                    "val_exact_match": res["A"]["field_exact_match"], "val_wilson95": res["A"]["wilson95"],
                    "val_valid_schema": res["A"]["valid_schema_rate"], "val_record_exact": res["A"]["record_exact_match"],
                    "val_B": res["B"]["both_correct"], "val_C": res["C"]["overall"], "val_D": res["D"]["all_checks"],
                    "train_tokens": r["train_tokens"], "cost_usd": round(train_usd, 4),
                    "exact_match_per_dollar": round(res["A"]["field_exact_match"] / max(train_usd, 1e-6), 1)})
        print(json.dumps(pts[-1]), flush=True)
    old = json.loads((EVAL_DIR / "tinker_learning_curve.json").read_text())["points"] if (EVAL_DIR / "tinker_learning_curve.json").exists() else []
    merged = {p["run"]: p for p in old + pts}
    base = json.loads(base_p.read_text())["A"]["field_exact_match"] if base_p.exists() else None
    write_eval_json("tinker_learning_curve.json", {
        "split": "val", "metric": "task A field-level exact match", "base_model_val_exact_match_local": base,
        "points": sorted(merged.values(), key=lambda p: p["n_examples"])}, "python -m training.tinker.learning_curve")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
