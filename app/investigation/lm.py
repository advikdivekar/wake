"""Swappable language-model interface (selected by config.yaml: language_model.backend)."""
from __future__ import annotations

import abc
import os

import httpx

from app.common.config import load_config


class LanguageModel(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def chat(self, messages: list[dict], max_tokens: int = 400) -> str: ...


class LlamaCppLM(LanguageModel):
    """Local llama.cpp server (OpenAI-compatible). Base GGUF + optional LoRA GGUF; no network beyond localhost."""

    def __init__(self, server: str, name: str = "qwen3-8b (llama.cpp, local)", lora_scale: float | None = None):
        self.server, self.name, self.lora_scale = server.rstrip("/"), name, lora_scale

    def chat(self, messages, max_tokens=400):
        body = {"messages": messages, "max_tokens": max_tokens, "temperature": 0, "seed": 0,
                "chat_template_kwargs": {"enable_thinking": False}}
        if self.lora_scale is not None:
            body["lora"] = [{"id": 0, "scale": self.lora_scale}]
        r = httpx.post(f"{self.server}/v1/chat/completions", json=body, timeout=300)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


class TinkerLM(LanguageModel):
    """Hosted Tinker sampling (used for training-time evaluation only; never at app runtime by default)."""

    def __init__(self, model_path: str | None, base_model: str = "Qwen/Qwen3-8B"):
        import tinker
        from tinker_cookbook import renderers
        from tinker_cookbook.tokenizer_utils import get_tokenizer
        self.sc = tinker.ServiceClient()
        self.client = (self.sc.create_sampling_client(model_path=model_path) if model_path
                       else self.sc.create_sampling_client(base_model=base_model))
        self.tok = get_tokenizer(base_model)
        self.renderer = renderers.get_renderer("qwen3_disable_thinking", self.tok)
        self.name = f"tinker:{model_path or base_model}"

    def chat(self, messages, max_tokens=400):
        import tinker
        prompt = self.renderer.build_generation_prompt(messages)
        params = tinker.SamplingParams(max_tokens=max_tokens, temperature=0.0,
                                       stop=self.renderer.get_stop_sequences())
        res = self.client.sample(prompt=prompt, sampling_params=params, num_samples=1).result()
        msg, _ = self.renderer.parse_response(res.sequences[0].tokens)
        return msg["content"] if isinstance(msg["content"], str) else str(msg["content"])


class TemplateLM(LanguageModel):
    """No-LM fallback: deterministic templates built by the caller (the card stays fully traceable)."""
    name = "template (no language model)"

    def chat(self, messages, max_tokens=400):
        raise NotImplementedError("TemplateLM does not generate; callers use deterministic templates")


def get_lm(backend: str | None = None) -> LanguageModel:
    cfg = load_config()["language_model"]
    backend = backend or os.environ.get("LM_BACKEND") or cfg["backend"]
    if backend == "llamacpp":
        return LlamaCppLM(cfg["server"], name="qwen3-8b+lora (llama.cpp, local)")
    if backend == "tinker":
        return TinkerLM(cfg.get("tinker_model_path"), cfg["base_model"])
    return TemplateLM()
