"""Tinker cost guard: estimate every job locally BEFORE submitting it and refuse to exceed the budget.

Prices (USD per 1M tokens) from https://thinkingmachines.ai/tinker/pricing/ dated 2026-10-19.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from app.common.paths import ROOT, now_iso

PRICES = {"Qwen/Qwen3-8B": {"prefill": 0.195, "sample": 0.60, "train": 0.44}}
LEDGER = ROOT / "evaluations" / "tinker_cost.json"


@lru_cache
def tokenizer(model="Qwen/Qwen3-8B"):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model)


def count_tokens(texts, model="Qwen/Qwen3-8B") -> int:
    tok = tokenizer(model)
    return sum(len(tok.encode(t)) for t in texts)


def ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"produced_by": "training/tinker/budget.py", "prices_per_1M": PRICES, "jobs": []}


def spent() -> float:
    return sum(j["est_usd"] for j in ledger()["jobs"])


def budget() -> float:
    return float(os.environ.get("TINKER_BUDGET_USD", "3.0"))


def estimate(kind: str, tokens: int, model="Qwen/Qwen3-8B") -> float:
    return tokens / 1e6 * PRICES[model][kind]


def authorize(job: str, costs: dict[str, int], model="Qwen/Qwen3-8B") -> float:
    """costs: {"train": n_tokens, "prefill": n, "sample": n}. Raises if over budget."""
    est = sum(estimate(k, v, model) for k, v in costs.items())
    if spent() + est > budget():
        raise SystemExit(f"BUDGET REFUSED: {job} est ${est:.3f}; spent ${spent():.3f}; cap ${budget():.2f}")
    return est


def record(job: str, costs: dict[str, int], est: float, model="Qwen/Qwen3-8B", note: str = "") -> None:
    L = ledger()
    L["jobs"].append({"at": now_iso(), "job": job, "model": model, "tokens": costs, "est_usd": round(est, 4),
                      "note": note})
    L["total_est_usd"] = round(sum(j["est_usd"] for j in L["jobs"]), 4)
    LEDGER.write_text(json.dumps(L, indent=2))
    with open(ROOT / "COST_LOG.md", "a") as f:
        f.write(f"| {now_iso()} | {job} | {costs} | {est:.4f} | {L['total_est_usd']:.4f} |\n")
