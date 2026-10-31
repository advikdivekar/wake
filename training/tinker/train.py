"""LoRA SFT on Tinker (hosted). Loss on assistant tokens only. Budget-guarded. Per-epoch sampler checkpoints.

Usage:
  python -m training.tinker.train --n 50  --name lc-n50        # learning-curve point (stratified subset)
  python -m training.tinker.train --n all --name final
Writes evaluations/tinker_runs.json (checkpoint paths, tokens, losses, est. cost).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time

from app.common.config import env
from app.common.paths import DATA_PROCESSED, EVAL_DIR, now_iso
from training.tinker import budget

SFT = DATA_PROCESSED / "sft"
RUNS = EVAL_DIR / "tinker_runs.json"


def subset(rows: list[dict], n: int | None, seed: int = 0) -> list[dict]:
    """Stratified (by task) nested subsets: the n=50 subset is contained in n=100, etc."""
    if n is None or n >= len(rows):
        return rows
    rng = random.Random(seed)
    by = {}
    for r in rows:
        by.setdefault(r["task"], []).append(r)
    for v in by.values():
        rng.shuffle(v)
    out = []
    for t, v in by.items():
        out += v[: max(1, round(n * len(v) / len(rows)))]
    return out[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", default="all")
    ap.add_argument("--name", required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--rank", type=int, default=int(env("TINKER_LORA_RANK", "16")))
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    base_model = env("TINKER_BASE_MODEL", "Qwen/Qwen3-8B")

    import tinker
    from tinker_cookbook import renderers
    from tinker_cookbook.supervised.common import datum_from_model_input_weights
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    rows = [json.loads(l) for l in open(SFT / "train.jsonl")]
    rows = subset(rows, None if a.n == "all" else int(a.n))
    tok = get_tokenizer(base_model)
    renderer = renderers.get_renderer("qwen3_disable_thinking", tok)
    data = []
    for r in rows:
        mi, w = renderer.build_supervised_example(r["messages"], train_on_what=renderers.TrainOnWhat.LAST_ASSISTANT_MESSAGE)
        data.append(datum_from_model_input_weights(mi, w, max_length=2048))
    tokens_per_epoch = sum(d.model_input.length for d in data)
    train_tokens = tokens_per_epoch * a.epochs
    est = budget.authorize(f"train:{a.name}", {"train": train_tokens}, base_model)
    lr = a.lr
    if lr is None:
        try:
            from tinker_cookbook.hyperparam_utils import get_lr
            lr = get_lr(base_model)
        except Exception:
            lr = 2e-4
    print(f"{a.name}: {len(data)} examples, {tokens_per_epoch} tok/epoch, {a.epochs} epochs, est ${est:.3f}, lr {lr:.2e}", flush=True)
    if a.dry_run:
        return

    sc = tinker.ServiceClient()
    tc = sc.create_lora_training_client(base_model=base_model, rank=a.rank)
    steps_per_epoch = math.ceil(len(data) / a.batch)
    total = steps_per_epoch * a.epochs
    rng = random.Random(1)
    log, ckpts, step = [], [], 0
    t0 = time.time()
    for ep in range(a.epochs):
        order = list(range(len(data))); rng.shuffle(order)
        for b in range(steps_per_epoch):
            batch = [data[i] for i in order[b * a.batch:(b + 1) * a.batch]]
            lr_t = lr * (1 - step / total)          # linear decay
            fb = tc.forward_backward(batch, loss_fn="cross_entropy")
            op = tc.optim_step(tinker.AdamParams(learning_rate=lr_t, beta1=0.9, beta2=0.95, eps=1e-8))
            res = fb.result(); op.result()
            lp = [x for o in res.loss_fn_outputs for x in o["logprobs"].tolist()]
            ws = [x for d in batch for x in d.loss_fn_inputs["weights"].tolist()]
            nll = -sum(l * w for l, w in zip(lp, ws)) / max(sum(ws), 1)
            log.append({"step": step, "epoch": ep, "nll": round(nll, 4), "lr": lr_t})
            if step % 5 == 0:
                print(f"  step {step}/{total} epoch {ep} nll {nll:.4f}", flush=True)
            step += 1
        path = tc.save_weights_for_sampler(name=f"{a.name}-ep{ep + 1}").result().path
        ckpts.append({"epoch": ep + 1, "sampler_path": path})
        print(f"  saved {path}", flush=True)
    budget.record(f"train:{a.name}", {"train": train_tokens}, est, base_model,
                  note=f"{len(data)} ex x {a.epochs} ep, rank {a.rank}")
    runs = json.loads(RUNS.read_text()) if RUNS.exists() else {"produced_by": "python -m training.tinker.train", "runs": []}
    runs["runs"] = [r for r in runs["runs"] if r["name"] != a.name] + [{
        "name": a.name, "n_examples": len(data), "base_model": base_model, "rank": a.rank, "lr": lr, "epochs": a.epochs,
        "batch": a.batch, "tokens_per_epoch": tokens_per_epoch, "train_tokens": train_tokens, "est_usd": round(est, 4),
        "checkpoints": ckpts, "loss_log": log, "minutes": round((time.time() - t0) / 60, 1), "finished_at": now_iso()}]
    RUNS.write_text(json.dumps(runs, indent=1))


if __name__ == "__main__":
    main()
