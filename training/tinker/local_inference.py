"""Offline proof: run the fine-tuned adapter LOCALLY (llama.cpp, Q4_K_M base + GGUF LoRA), no Tinker calls.

Starts a private llama-server on :8082 with HF_HUB_OFFLINE=1, runs N held-out TEST passages (task A),
scores them with the frozen spec, and compares with the Tinker-sampled outputs if available.
Usage: python -m training.tinker.local_inference --offline [--n 20]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import time

import httpx

from app.common.paths import DATA_PROCESSED, MODELS_DIR, write_eval_json
from app.investigation.lm import LlamaCppLM
from training.tinker import spec
from training.tinker.scoring import score_A

PORT = 8082


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--split", default="val")
    ap.add_argument("--compare", default="tuned-offline-n200-v2_tinker_val.jsonl",
                    help="Tinker-sampled outputs of the SAME checkpoint, for quantisation parity")
    a = ap.parse_args()
    env = {**os.environ}
    if a.offline:
        env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
        env.pop("TINKER_API_KEY", None)        # prove no Tinker credentials are even available
    base, lora = MODELS_DIR / "Qwen3-8B-Q4_K_M.gguf", MODELS_DIR / "adapter.gguf"
    cmd = ["llama-server", "-m", str(base), "--lora", str(lora), "--port", str(PORT), "-c", "8192", "--jinja", "-ngl", "99"]
    srv = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    try:
        for _ in range(120):
            try:
                if httpx.get(f"http://localhost:{PORT}/health", timeout=2).json().get("status") == "ok":
                    break
            except Exception:
                pass
            time.sleep(1)
        allx = [json.loads(l) for l in open(DATA_PROCESSED / "sft" / f"{a.split}.jsonl")]
        idx = [i for i, e in enumerate(allx) if e["task"] == "A" and e.get("provenance") == "real"][: a.n]
        exs = [allx[i] for i in idx]
        lm = LlamaCppLM(f"http://localhost:{PORT}", name="local llama.cpp + adapter.gguf")
        outs, secs = [], []
        for e in exs:
            t = time.time()
            outs.append(lm.chat(e["messages"][:-1], max_tokens=400)); secs.append(time.time() - t)
        res = {k: v for k, v in score_A(exs, outs).items() if not k.startswith("_")}
        agree = None
        tk = DATA_PROCESSED / "sft" / "outputs" / a.compare
        if tk.exists():
            tko = {json.loads(l)["i"]: json.loads(l)["output"] for l in open(tk)}
            same = []
            for j, i in enumerate(idx):
                p1, _ = spec.parse_lines(outs[j]); p2, _ = spec.parse_lines(tko.get(i, ""))
                if p1 and p2:
                    same += [spec.field_equal(f, p1[f], p2[f]) for f in spec.FIELDS]
            agree = round(sum(same) / max(len(same), 1), 4)
        write_eval_json("offline_inference.json", {
            "setup": {"runtime": "llama.cpp llama-server (local)", "base": base.name, "adapter": lora.name,
                      "quantisation": "Q4_K_M base + f16 LoRA", "offline_env": a.offline,
                      "tinker_api_key_present": "TINKER_API_KEY" in env, "machine": platform.machine(),
                      "note": "Training ran on Tinker's hosted service; this inference made no Tinker calls."},
            "split": f"{a.split} (real passages from held-out documents; never trained on)",
            "adapter_run": json.loads((MODELS_DIR / "adapter_source.json").read_text()) if (MODELS_DIR / "adapter_source.json").exists() else None,
            "n_passages": len(exs), "seconds_per_passage": round(sum(secs) / max(len(secs), 1), 2),
            "task_A": res, "field_agreement_with_tinker_bf16_outputs": agree,
            "sample": [{"passage": e["passage"][:300], "output": o} for e, o in zip(exs[:3], outs[:3])]},
            "python -m training.tinker.local_inference --offline")
        print(json.dumps({"field_exact_match": res["field_exact_match"], "agreement_with_tinker": agree}))
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
