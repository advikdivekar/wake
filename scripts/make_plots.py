"""Static PNG versions of the evaluation charts (the console renders interactive versions from the same JSON)."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from app.common.paths import EVAL_DIR

SURF, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
S1, S2, S3, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#b5b3ad"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.6, "legend.frameon": False})


def j(n):
    return json.loads((EVAL_DIR / n).read_text())


def label(m):
    return {"tabpfn-v2": "TabPFN-v2", "rf": "Random Forest", "xgboost": "XGBoost", "lightgbm": "LightGBM",
            "lr": "Logistic Reg.", "iforest": "Isolation Forest", "rule": "Zero-fraction rule"}.get(m.split(":")[0], m)


def pr_curve():
    c = j("pr_curve.json")["curves"]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    order = sorted(c, key=lambda m: m.split(":")[0] not in ("tabpfn-v2", "rf", "xgboost"))
    colors = {"tabpfn-v2": S1, "rf": S2, "xgboost": S3}
    for m in reversed(order):
        pts = c[m]
        col = colors.get(m.split(":")[0], GRAY)
        ax.plot([p["recall"] for p in pts], [p["precision"] for p in pts], color=col, lw=2 if col != GRAY else 1.2,
                label=label(m), zorder=3 if col != GRAY else 2)
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.set_ylim(0.2, 1.01); ax.set_xlim(0, 1.01)
    ax.set_title("Precision-recall, official OPSSAT-AD test split (529 segments)", loc="left", fontsize=11)
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout(); fig.savefig(EVAL_DIR / "pr_curve.png", dpi=160); plt.close(fig)


def calibration():
    c = j("calibration.json")
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.plot([0, 1], [0, 1], color=GRAY, lw=1.2, ls="--", label="Perfect calibration")
    ax.plot([b["p_mean"] for b in c["bins"]], [b["frac_pos"] for b in c["bins"]], color=S1, lw=2, marker="o", ms=6,
            markeredgecolor=SURF, markeredgewidth=2, label=f"TabPFN-v2 (Brier {c['brier']:.4f})")
    ax.set_xlabel("Predicted P(anomalous)"); ax.set_ylabel("Observed fraction anomalous")
    ax.set_title("Calibration, test split", loc="left", fontsize=11); ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout(); fig.savefig(EVAL_DIR / "calibration.png", dpi=160); plt.close(fig)


def tradeoff():
    t = pd.read_csv(EVAL_DIR / "threshold_tradeoff.csv")
    th = j("thresholds.json")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(t.threshold, t.missed_anomalies, color=S2, lw=2, label="Missed anomalies")
    ax.plot(t.threshold, t.false_alerts, color=S1, lw=2, label="False alerts")
    for k, name in (("low", "queue"), ("f1", "max-F1"), ("high", "prioritise")):
        ax.axvline(th[k], color=GRAY, lw=1, ls=":")
        ax.text(th[k], ax.get_ylim()[1] * 0.95, f" {name} {th[k]:.2f}", color=MUTED, fontsize=8, va="top")
    ax.set_xlabel("Decision threshold on P(anomalous)"); ax.set_ylabel("Segments (training OOF, n=1,594)")
    ax.set_title("Missed anomalies vs false alerts (thresholds chosen on training data)", loc="left", fontsize=11)
    ax.legend(loc="center right", fontsize=8.5)
    fig.tight_layout(); fig.savefig(EVAL_DIR / "threshold_tradeoff.png", dpi=160); plt.close(fig)


def learning_curve():
    lc = j("tinker_learning_curve.json")
    pts = [p for p in lc["points"] if p["run"].startswith("lc-") or p["run"] == "final-v2"]
    pts.sort(key=lambda p: p["n_examples"])
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    if lc.get("base_model_val_exact_match_local") is not None:
        ax.axhline(lc["base_model_val_exact_match_local"], color=GRAY, lw=1.2, ls="--")
        ax.text(pts[0]["n_examples"], lc["base_model_val_exact_match_local"] + 0.005, "base Qwen3-8B (no tuning)",
                color=MUTED, fontsize=8)
    ax.plot([p["n_examples"] for p in pts], [p["val_exact_match"] for p in pts], color=S1, lw=2, marker="o", ms=7,
            markeredgecolor=SURF, markeredgewidth=2)
    for p in pts:
        ax.annotate(f"{p['val_exact_match']:.3f}\n${p['cost_usd']:.3f}", (p["n_examples"], p["val_exact_match"]),
                    textcoords="offset points", xytext=(0, -26), ha="center", fontsize=8, color=MUTED)
    ax.axhline(0.95, color=S2, lw=1, ls=":"); ax.text(pts[0]["n_examples"], 0.955, "95% target (set before training)", fontsize=8, color=MUTED)
    ax.text(0.99, 0.03, "n=50/100/200: trained on spec-v1 labels, scored on v2 gold; n=445: trained on v2",
            transform=ax.transAxes, ha="right", fontsize=7.5, color=MUTED)
    ax.set_xlabel("Training examples (3 epochs)"); ax.set_ylabel("VAL field-level exact match (task A)")
    ax.set_ylim(0.6, 1.0)
    ax.set_title("Tinker learning curve: accuracy and training cost", loc="left", fontsize=11)
    fig.tight_layout(); fig.savefig(EVAL_DIR / "tinker_learning_curve.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    pr_curve(); calibration(); tradeoff(); learning_curve()
    print("wrote 4 PNGs")
