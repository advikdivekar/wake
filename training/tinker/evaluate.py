"""Evaluate base vs fine-tuned interpreter on tasks A-D (same prompts, parser, validator).

Backends:  local  -> llama-server (Q4_K_M GGUF; base = LoRA scale 0, tuned = LoRA scale 1), free
           tinker -> Tinker sampling client (costs tokens; budget-guarded)
Usage:
  python -m training.tinker.evaluate --model base  --split val  [--backend local]
  python -m training.tinker.evaluate --model tuned --split val  --tag n200
  python -m training.tinker.evaluate --final        # TEST split, once per config (guarded), writes tinker_eval_*.json
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor

from app.common.config import load_config
from app.common.paths import DATA_PROCESSED, EVAL_DIR, write_eval_json
from app.investigation.lm import LlamaCppLM, TinkerLM
from training.tinker.scoring import SCORERS, mcnemar

SFT = DATA_PROCESSED / "sft"
OUTS = SFT / "outputs"
OUTS.mkdir(parents=True, exist_ok=True)
MAX_TOK = {"A": 400, "B": 400, "C": 200, "D": 400}


def load(split):
    return [json.loads(l) for l in open(SFT / f"{split}.jsonl")]


def get_model(model: str, backend: str, tinker_path: str | None):
    cfg = load_config()["language_model"]
    if backend == "local":
        from app.common.paths import ROOT
        has_adapter = (ROOT / cfg["adapter"]).exists()
        scale = (0.0 if model == "base" else 1.0) if has_adapter else None
        return LlamaCppLM(cfg["server"], name=f"local:{model}", lora_scale=scale)
    if model == "base":
        return TinkerLM(None, cfg["base_model"])
    return TinkerLM(tinker_path or cfg.get("tinker_model_path"), cfg["base_model"])


def run(model: str, split: str, backend: str, tag: str = "", tinker_path=None, workers=2) -> list[dict]:
    exs = load(split)
    out_path = OUTS / f"{model}{('-' + tag) if tag else ''}_{backend}_{split}.jsonl"
    done = {}
    if out_path.exists():
        for l in open(out_path):
            r = json.loads(l); done[r["i"]] = r
    lm = get_model(model, backend, tinker_path)
    todo = [i for i in range(len(exs)) if i not in done]

    def one(i):
        ex = exs[i]
        msgs = ex["messages"][:-1]
        t = time.time()
        try:
            out = lm.chat(msgs, max_tokens=MAX_TOK[ex["task"]])
        except Exception as e:
            out = f"__ERROR__ {type(e).__name__}: {e}"
        return {"i": i, "task": ex["task"], "output": out, "seconds": round(time.time() - t, 2)}

    with open(out_path, "a") as f, ThreadPoolExecutor(workers) as pool:
        for k, r in enumerate(pool.map(one, todo)):
            f.write(json.dumps(r) + "\n"); f.flush(); done[r["i"]] = r
            if k % 20 == 0:
                print(f"{model}/{split}: {len(done)}/{len(exs)}", flush=True)
    return [done[i] for i in range(len(exs))]


def score(split: str, outputs: list[dict]) -> dict:
    exs = load(split)
    res = {}
    for task, fn in SCORERS.items():
        idx = [i for i, e in enumerate(exs) if e["task"] == task]
        if idx:
            res[task] = fn([exs[i] for i in idx], [outputs[i]["output"] for i in idx])
    return res


def strip(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["base", "tuned"], default="base")
    ap.add_argument("--split", choices=["train", "val", "test"], default="val")
    ap.add_argument("--backend", choices=["local", "tinker"], default="local")
    ap.add_argument("--tag", default="")
    ap.add_argument("--tinker-path", default=None)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.final:
        from training.tabpfn.evaluate import guard
        guard("tinker_test", {"adapter": load_config()["language_model"]["adapter"], "backend": a.backend,
                              "tag": a.tag}, a.force)
        base = score("test", run("base", "test", a.backend))
        tuned = score("test", run("tuned", "test", a.backend, a.tag, a.tinker_path))
        for task in base:
            write_eval_json(f"tinker_eval_{task}.json", {
                "split": "test (held-out document families)", "backend": a.backend,
                "base": strip(base[task]), "tuned": strip(tuned[task]),
                "paired": mcnemar(base[task]["_cells"], tuned[task]["_cells"])},
                f"python -m training.tinker.evaluate --final --backend {a.backend}")
            print(task, "base", base[task].get("field_exact_match", base[task].get("overall", base[task].get("all_checks", base[task].get("both_correct")))),
                  "tuned", tuned[task].get("field_exact_match", tuned[task].get("overall", tuned[task].get("all_checks", tuned[task].get("both_correct")))))
        return
    outs = run(a.model, a.split, a.backend, a.tag, a.tinker_path)
    res = score(a.split, outs)
    name = f"tinker_{a.split}_{a.model}{('-' + a.tag) if a.tag else ''}_{a.backend}.json"
    write_eval_json(name, {k: strip(v) for k, v in res.items()},
                    f"python -m training.tinker.evaluate --model {a.model} --split {a.split} --backend {a.backend}")
    for t, r in res.items():
        print(t, json.dumps({k: v for k, v in strip(r).items() if k != "per_field"}))


if __name__ == "__main__":
    main()
