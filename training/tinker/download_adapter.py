"""Download the trained LoRA from Tinker, export as a PEFT adapter, convert to GGUF for llama.cpp.

Usage: python -m training.tinker.download_adapter --run final [--epoch N]
Produces models/adapter_peft/ (PEFT: adapter_config.json + adapter_model.safetensors) and models/adapter.gguf
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

from app.common.config import env
from app.common.paths import EVAL_DIR, MODELS_DIR, ROOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="final")
    ap.add_argument("--epoch", type=int, default=None)
    a = ap.parse_args()
    base = env("TINKER_BASE_MODEL", "Qwen/Qwen3-8B")
    runs = json.loads((EVAL_DIR / "tinker_runs.json").read_text())["runs"]
    run = next(r for r in runs if r["name"] == a.run)
    ck = run["checkpoints"][-1] if a.epoch is None else next(c for c in run["checkpoints"] if c["epoch"] == a.epoch)
    from tinker_cookbook import weights
    raw = MODELS_DIR / "adapter_raw"
    peft = MODELS_DIR / "adapter_peft"
    for p in (raw, peft):
        shutil.rmtree(p, ignore_errors=True)
    weights.download(tinker_path=ck["sampler_path"], output_dir=str(raw))
    weights.build_lora_adapter(base_model=base, adapter_path=str(raw), output_path=str(peft))
    print("PEFT adapter:", sorted(p.name for p in peft.iterdir()))
    conv = ROOT / "third_party" / "llama_cpp" / "convert_lora_to_gguf.py"
    subprocess.run([sys.executable, str(conv), str(peft), "--base-model-id", base,
                    "--outfile", str(MODELS_DIR / "adapter.gguf"), "--outtype", "f16"], check=True,
                   env={**__import__("os").environ, "PYTHONPATH": str(conv.parent)})
    (MODELS_DIR / "adapter_source.json").write_text(json.dumps({"run": a.run, **ck, "base_model": base}, indent=1))
    print("wrote", MODELS_DIR / "adapter.gguf")


if __name__ == "__main__":
    main()
