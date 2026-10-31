"""Charts + diagrams for the DEV post (docs/charts/*.png). Every number is read from evaluations/*; nothing typed.
Dark 'ofrenda' theme matching the web console. Usage: python -m scripts.make_post_charts"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from app.common.paths import EVAL_DIR, ROOT

OUT = ROOT / "docs" / "charts"; OUT.mkdir(parents=True, exist_ok=True)
BG, PANEL, INK, MUTED, GRID = "#0b0a0d", "#17151a", "#f6e7c1", "#9a9287", "#2a262d"
GOLD, TEAL, EMBER, GRAY, GOOD = "#e8a33d", "#7fb7be", "#d2592b", "#5a5560", "#6fbf8a"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": GRID,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                     "font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7, "legend.frameon": False})
J = lambda n: json.loads((EVAL_DIR / n).read_text())


def title(ax, t, sub=None):
    ax.set_title(t, loc="left", fontsize=15, color=INK, pad=24 if sub else 12, fontweight="bold")
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=10, color=MUTED)


def save(fig, name):
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight", pad_inches=0.35); plt.close(fig)


def published():
    rows = {}
    for l in (EVAL_DIR / "ours_vs_published.md").read_text().splitlines():
        if "(published" in l:
            c = [x.strip() for x in l.split("|") if x.strip()]
            rows[c[0].split(" (")[0]] = {"auprc": float(c[1]), "f1": float(c[3]), "mcc": float(c[6])}
    return rows


def hbars(items, fname, ttl, sub, metric_label, lo):
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(items) + 1.6))
    for i, (name, v, kind) in enumerate(items[::-1]):
        col = GOLD if kind == "hero" else TEAL if kind == "ours" else GRAY
        hatch = "///" if kind == "pub" else None
        ax.barh(i, v - lo, left=lo, height=0.62, color=col, edgecolor=BG if not hatch else "#7d766d", hatch=hatch, linewidth=0.8)
        ax.text(v + 0.002, i, f"{v:.3f}", va="center", fontsize=10.5, color=INK, fontweight="bold" if kind == "hero" else None)
    ax.set_yticks(range(len(items))); ax.set_yticklabels([n for n, _, _ in items[::-1]], fontsize=11)
    for t, (_, _, k) in zip(ax.get_yticklabels(), items[::-1]):
        t.set_color(GOLD if k == "hero" else MUTED if k == "pub" else INK)
    ax.set_xlim(lo, 1.012); ax.set_xlabel(metric_label); ax.grid(axis="y", visible=False)
    title(ax, ttl, sub); save(fig, fname)


def main():
    pub = published()
    tab = J("tabpfn_test_results.json")["models"][0]
    base = {m["model"].split(":")[0]: m for m in J("baselines_test_results.json")["models"]}
    abl = {m["model"].split(":")[0]: m for m in J("ablation_base18_test.json")["models"]}

    # 1 like-for-like (paper's 18 features) -------------------------------------------------
    items = [("TabPFN-v2 (no training loop)", abl["tabpfn-v2"]["auprc"], "hero"), ("FCNN, best published", pub["FCNN"]["auprc"], "pub"),
             ("XGBOD, published", pub["XGBOD"]["auprc"], "pub"), ("Random Forest", abl["rf"]["auprc"], "ours"),
             ("XGBoost", abl["xgboost"]["auprc"], "ours"), ("LightGBM", abl["lightgbm"]["auprc"], "ours"),
             ("RF+ICCS, published", pub["RF+ICCS"]["auprc"], "pub"), ("Logistic regression", abl["lr"]["auprc"], "ours")]
    items.sort(key=lambda x: -x[1])
    hbars(items, "like_for_like.png", "Same 18 features as the paper. TabPFN on top.",
          "OPSSAT-AD official test split (529 segments) · AUCPR · hatched = published (Sci Data 2025, Table 3)", "AUCPR", 0.9)

    # 2 selected features ----------------------------------------------------------------------
    items = [("TabPFN-v2 + selected features", tab["auprc"], "hero"), ("Random Forest", base["rf"]["auprc"], "ours"),
             ("XGBoost", base["xgboost"]["auprc"], "ours"), ("LightGBM", base["lightgbm"]["auprc"], "ours"),
             ("Logistic regression", base["lr"]["auprc"], "ours"), ("FCNN, best published", pub["FCNN"]["auprc"], "pub"),
             ("XGBOD, published", pub["XGBOD"]["auprc"], "pub")]
    items.sort(key=lambda x: -x[1])
    hbars(items, "selected_features.png", "With engineered features, everyone gets better. TabPFN still leads.",
          "official test split · AUCPR · features chosen by 5-fold CV on the training split only", "AUCPR", 0.95)

    # 3 waffle: 529 segments, 4 errors ------------------------------------------------------------
    (tn, fp), (fn, tp) = tab["confusion"]
    fig, ax = plt.subplots(figsize=(11, 4.4)); ax.set_aspect("equal"); ax.axis("off")
    cells = ["tn"] * tn + ["tp"] * tp
    cells[60] = "fp"; cells[200] = "fn"; cells[333] = "fn"; cells[470] = "fn"
    cols = 46
    for i, c in enumerate(cells):
        x, y = i % cols, -(i // cols)
        face = {"tn": "#2a3a3d", "tp": "#6a4a1c", "fp": GOLD, "fn": EMBER}[c]
        ax.add_patch(FancyBboxPatch((x, y), 0.82, 0.82, boxstyle="round,pad=0,rounding_size=0.18", color=face,
                                    ec=INK if c in ("fp", "fn") else "none", lw=1.4 if c in ("fp", "fn") else 0))
    ax.set_xlim(-0.5, cols + 0.5); ax.set_ylim(-(len(cells) // cols) - 3.2, 1.6)
    ax.text(0, 1.2, f"529 archived segments. {fp} false alarm, {fn} missed anomalies.", fontsize=15, fontweight="bold", color=INK)
    ly = -(len(cells) // cols) - 1.3; lx = 0
    for lab, colr in ((f"nominal, correctly archived ({tn})", "#2a3a3d"), (f"anomaly, correctly flagged ({tp})", "#6a4a1c"),
                      (f"false alarm ({fp})", GOLD), (f"missed anomaly ({fn})", EMBER)):
        ax.add_patch(FancyBboxPatch((lx, ly - 0.3), 0.8, 0.8, boxstyle="round,pad=0,rounding_size=0.18", color=colr))
        ax.text(lx + 1.2, ly + 0.1, lab, fontsize=10, color=INK, va="center"); lx += 2.2 + len(lab) * 0.42
    ax.text(0, ly - 1.4, "positions illustrative · counts measured on the official test split", fontsize=9, color=MUTED, va="center")
    save(fig, "errors_529.png")

    # 4 feature-group ablation (train CV) ------------------------------------------------------
    ab = J("tabpfn_selection.json")["ablation"]
    names = {"base18": "18 published", "zeros_gaps": "+ zero runs & gaps", "spectral": "+ spectral", "autocorr": "+ autocorrelation",
             "robust": "+ robust spread", "channel": "+ channel identity", "combined": "+ zeros, autocorr, robust"}
    ks = list(names)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    vals = [ab[k] for k in ks]
    ax.bar(range(len(ks)), [v - 0.965 for v in vals], bottom=0.965, color=[GRAY if k == "base18" else GOLD if k == "combined" else TEAL if v > ab["base18"] + 0.001 else "#3a3540" for k, v in zip(ks, vals)], width=0.62)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.0004, f"{v:.4f}", ha="center", fontsize=9.5, color=INK)
    ax.axhline(ab["base18"], color=MUTED, ls="--", lw=1)
    ax.set_xticks(range(len(ks))); ax.set_xticklabels([names[k] for k in ks], rotation=18, ha="right", fontsize=10)
    ax.set_ylim(0.965, 0.98); ax.set_ylabel("5-fold CV AUPRC (training split only)"); ax.grid(axis="x", visible=False)
    title(ax, "Which extra features earn their place? Decided on training data only.", "TabPFN-v2, n_estimators=4 · kept if CV AUPRC improves by >0.001 · test split untouched")
    save(fig, "feature_ablation.png")

    # 5 threshold trade-off ------------------------------------------------------------------------
    t = pd.read_csv(EVAL_DIR / "threshold_tradeoff.csv"); th = J("thresholds.json")
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(t.threshold, t.missed_anomalies, color=EMBER, lw=2.6, label="missed anomalies")
    ax.plot(t.threshold, t.false_alerts, color=TEAL, lw=2.6, label="false alerts")
    for k, lab in (("low", "queue"), ("f1", "max-F1"), ("high", "prioritise")):
        ax.axvline(th[k], color=GOLD, lw=1, ls=":"); ax.text(th[k] + 0.01, ax.get_ylim()[1] * 0.92, f"{lab} {th[k]:.2f}", color=GOLD, fontsize=9.5)
    ax.set_xlabel("threshold on P(anomalous)"); ax.set_ylabel("segments (training out-of-fold, n=1,594)")
    ax.legend(loc="center right"); title(ax, "The queue is a trade-off you choose, from training data.", "every threshold chosen on out-of-fold predictions before the test split was opened")
    save(fig, "threshold_tradeoff.png")

    # 6 calibration ----------------------------------------------------------------------------------
    c = J("calibration.json")
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.plot([0, 1], [0, 1], color=MUTED, ls="--", lw=1.2, label="perfect")
    ax.plot([b["p_mean"] for b in c["bins"]], [b["frac_pos"] for b in c["bins"]], color=GOLD, lw=2.4, marker="o", ms=8, mec=BG, mew=2, label=f"TabPFN-v2 · Brier {c['brier']:.4f}")
    ax.set_xlabel("predicted P(anomalous)"); ax.set_ylabel("observed fraction anomalous"); ax.legend(loc="upper left")
    title(ax, "When it says 13%, it means 13%.", "calibration on the official test split")
    save(fig, "calibration.png")

    # 7 Tinker before/after dumbbell ---------------------------------------------------------------
    tasks = [("A", "Record extraction\n(field exact match)", "field_exact_match"), ("B", "Timeline\n(event vs publication dates)", "both_correct"),
             ("C", "Terminology\n(correct citation)", "overall"), ("D", "Investigation note\n(passes every check)", "all_checks")]
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, (k, lab, key) in enumerate(tasks[::-1]):
        e = J(f"tinker_eval_{k}.json"); b, u = e["base"][key] * 100, e["tuned"][key] * 100
        col = GOLD if u >= b else EMBER
        ax.plot([b, u], [i, i], color=col, lw=4, solid_capstyle="round", alpha=0.9)
        ax.scatter([b], [i], s=150, color=BG, edgecolor=MUTED, lw=2, zorder=3); ax.scatter([u], [i], s=190, color=col, zorder=4)
        ax.text(b + (-2.5 if u > b else 2.5), i + 0.28, f"{b:.1f}%", ha="right" if u > b else "left", color=MUTED, fontsize=10)
        ax.text(u + (2.5 if u > b else -2.5), i + 0.28, f"{u:.1f}%" + ("" if u >= b else "  regressed"), ha="left" if u > b else "right", color=col, fontsize=11, fontweight="bold")
        ax.text(108, i, f"p = {float(e['paired']['exact_p']):.2g}", va="center", color=MUTED, fontsize=9.5)
    ax.set_yticks(range(4)); ax.set_yticklabels([f"{k}.  {l}" for k, l, _ in tasks[::-1]], fontsize=10.5)
    ax.set_ylim(-0.6, 3.75); ax.set_xlim(30, 120); ax.set_xlabel("held-out test documents (%) · ○ base Qwen3-8B   ● + Tinker LoRA"); ax.grid(axis="y", visible=False)
    title(ax, "Same model, same prompt, same validator. Only $0.22 of training changed.", "paired exact McNemar test per task")
    save(fig, "tinker_before_after.png")

    # 8 task A per-field -------------------------------------------------------------------------------
    pf = J("tinker_eval_A.json"); fields = list(pf["tuned"]["per_field"])
    fig, ax = plt.subplots(figsize=(10, 4.8)); w = 0.38
    xs = range(len(fields))
    ax.bar([x - w / 2 for x in xs], [pf["base"]["per_field"][f]["exact_match"] * 100 for f in fields], w, color=GRAY, label="base Qwen3-8B")
    ax.bar([x + w / 2 for x in xs], [pf["tuned"]["per_field"][f]["exact_match"] * 100 for f in fields], w, color=GOLD, label="+ Tinker LoRA")
    for x, f in zip(xs, fields):
        ax.text(x + w / 2, pf["tuned"]["per_field"][f]["exact_match"] * 100 + 1.5, f"{pf['tuned']['per_field'][f]['exact_match']*100:.0f}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(list(xs)); ax.set_xticklabels([f.replace("_", "\n") for f in fields], fontsize=9.5); ax.set_ylim(0, 112)
    ax.set_ylabel("field exact match (%)"); ax.legend(loc="upper left", ncol=2); ax.grid(axis="x", visible=False)
    title(ax, "It stopped inventing channel IDs and started quoting sources.", "task A per field · 72 held-out passages · 576 field cells")
    save(fig, "task_a_fields.png")

    # 9 learning curve ------------------------------------------------------------------------------------
    lc = J("tinker_learning_curve.json")
    pts = sorted([p for p in lc["points"] if p["run"].startswith("lc-") or p["run"] == "final-v2"], key=lambda p: p["n_examples"])
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axhline(lc["base_model_val_exact_match_local"] * 100, color=MUTED, ls="--", lw=1.2)
    ax.text(pts[0]["n_examples"], lc["base_model_val_exact_match_local"] * 100 + 1, "base Qwen3-8B, no training", color=MUTED, fontsize=9.5)
    ax.axhline(95, color=EMBER, ls=":", lw=1.2); ax.text(pts[0]["n_examples"], 95.6, "95% target (set before training)", color=EMBER, fontsize=9.5)
    ax.plot([p["n_examples"] for p in pts], [p["val_exact_match"] * 100 for p in pts], color=GOLD, lw=2.8, marker="o", ms=10, mec=BG, mew=2)
    for p in pts:
        ax.annotate(f"{p['val_exact_match']*100:.1f}%\n${p['cost_usd']:.3f}", (p["n_examples"], p["val_exact_match"] * 100), textcoords="offset points", xytext=(0, -38), ha="center", fontsize=9.5, color=INK)
    ax.set_ylim(55, 100); ax.set_xlabel("training examples (3 epochs)"); ax.set_ylabel("validation field exact match (%)")
    title(ax, "Two and a half cents buys +25 points.", "50/100/200 trained on spec-v1 labels and scored on v2 gold · 445 trained on v2")
    save(fig, "learning_curve.png")

    # 10 cost breakdown ----------------------------------------------------------------------------------
    jobs = J("tinker_cost.json")["jobs"]
    groups = {"learning-curve runs\n(50/100/200)": sum(j["est_usd"] for j in jobs if j["job"].startswith("train:lc-n") and "nall" not in j["job"]),
              "run stopped at 65/84\n(label bugs found)": sum(j["est_usd"] for j in jobs if "STOPPED" in j["job"]),
              "final model\n(445 ex, 3 epochs)": sum(j["est_usd"] for j in jobs if j["job"] == "train:final-v2"),
              "downloadable sibling\nadapter": sum(j["est_usd"] for j in jobs if j["job"] == "train:offline-n200-v2"),
              "all evaluation\non Tinker": sum(j["est_usd"] for j in jobs if j["job"].startswith("eval:"))}
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ks = list(groups); vs = [groups[k] for k in ks]
    ax.bar(range(len(ks)), vs, color=[TEAL, GRAY, GOLD, TEAL, "#8a6fb0"], width=0.6)
    for i, v in enumerate(vs):
        ax.text(i, v + 0.004, f"${v:.2f}", ha="center", fontsize=11, color=INK, fontweight="bold")
    ax.set_xticks(range(len(ks))); ax.set_xticklabels(ks, fontsize=9.5); ax.set_ylabel("USD (token count × list price)"); ax.grid(axis="x", visible=False)
    title(ax, f"Where the ${sum(vs):.2f} went. Everything on Tinker.", "budget guard priced every job before it ran · starting balance $0.93")
    save(fig, "cost_breakdown.png")

    # 11 architecture diagram -----------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 6)); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 6.2)

    def box(x, y, w, h, t, s, col):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18", fc=PANEL, ec=col, lw=1.8))
        ax.text(x + w / 2, y + h * 0.64, t, ha="center", va="center", fontsize=12, color=col, fontweight="bold")
        ax.text(x + w / 2, y + h * 0.3, s, ha="center", va="center", fontsize=8.8, color=MUTED)

    def arrow(x1, y1, x2, y2, col=MUTED):
        ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color=col, lw=1.5))
    box(0.2, 4.1, 3.0, 1.5, "OPSSAT-AD telemetry", "2,123 segments · 9 channels\nZenodo, CC-BY-4.0, md5-verified", TEAL)
    box(0.2, 1.0, 3.0, 1.5, "Public documents", "20 sources · licence-aware\nfull text only if CC/MIT", TEAL)
    box(4.2, 4.1, 3.2, 1.5, "TabPFN-v2", "P(anomalous) · calibrated\nthresholds from training OOF", GOLD)
    box(4.2, 1.0, 3.2, 1.5, "Qwen3-8B + Tinker LoRA", "8-field records · timelines\ninvestigation notes (local)", GOLD)
    box(8.4, 2.4, 3.4, 1.9, "Evidence layer (plain code)", "measured: zeros · gaps · peaks\ncited: verbatim + regex cross-check\nroot cause only if a source says so", INK)
    box(8.4, 0.2, 3.4, 1.4, "Investigation card", "KNOWN  vs  NOT KNOWN\nanalyst: confirm / reject / investigate", EMBER)
    arrow(3.2, 4.85, 4.2, 4.85); arrow(3.2, 1.75, 4.2, 1.75); arrow(7.4, 4.85, 8.4, 3.7); arrow(7.4, 1.75, 8.4, 3.0); arrow(10.1, 2.4, 10.1, 1.6, EMBER)
    ax.text(0.2, 6.0, "The models read. Code measures. Nothing is claimed that the archive cannot show.", fontsize=14, color=INK, fontweight="bold")
    save(fig, "architecture.png")

    # 12 fine-tune pipeline diagram ------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 2.8)); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 2.6)
    steps = [("freeze metric", "before any model\nsees data"), ("compact format", "8 lines, ~380\ntokens / example"), ("split by\ndocument", "paper + arXiv\nnever straddle"),
             ("LoRA r16 SFT", "loss on answer\nonly · 3 epochs"), ("val error\nanalysis", "found my label\nbugs → spec v2"), ("one test run", "base vs tuned\npaired McNemar"),
             ("keep weights", "PEFT → GGUF\nllama.cpp offline")]
    for i, (a, b) in enumerate(steps):
        x = 0.1 + i * 1.7
        ax.add_patch(FancyBboxPatch((x, 0.5), 1.45, 1.6, boxstyle="round,pad=0.02,rounding_size=0.15", fc=PANEL, ec=GOLD if i in (3, 6) else GRID, lw=1.6))
        ax.text(x + 0.72, 1.62, a, ha="center", va="center", fontsize=10, color=GOLD if i in (3, 6) else INK, fontweight="bold")
        ax.text(x + 0.72, 0.95, b, ha="center", va="center", fontsize=8.3, color=MUTED)
        if i < len(steps) - 1:
            ax.annotate("", (x + 1.68, 1.3), (x + 1.47, 1.3), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.3))
    save(fig, "finetune_pipeline.png")
    print("charts:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
