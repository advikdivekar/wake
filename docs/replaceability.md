# Swapping components (no code changes)

Everything is configured in `config.yaml`:

```yaml
language_model:
  backend: llamacpp      # llamacpp | tinker | template
  base_model: Qwen/Qwen3-8B
  gguf: models/Qwen3-8B-Q4_K_M.gguf
  adapter: models/adapter.gguf
  server: http://localhost:8081
  tinker_model_path: null   # tinker://... (only for backend: tinker)
tabular_classifier:
  backend: tabpfn
  path: models/tabpfn_final.pkl   # any pickle with {model, features, name}; model must have predict_proba
thresholds: {high: ..., low: ..., f1: ...}   # written by training/tabpfn/threshold.py
retrieval: {embedding_model: BAAI/bge-small-en-v1.5, fusion: rrf, k: 6}
```

- **Language model.** Implement `app/investigation/lm.py::LanguageModel.chat(messages, max_tokens)`. The built-in backends are:
  - `LlamaCppLM` (local, the default),
  - `TinkerLM` (hosted sampling),
  - `TemplateLM` (no LM at all; the cards stay fully deterministic and traceable).

  You can also override the backend per process with `LM_BACKEND=template`.
- **Adapter.** Point `language_model.adapter` at any GGUF LoRA for the same base model. Run `make adapter` to rebuild it from a Tinker checkpoint.
- **Tabular classifier.** `app/prediction/base.py::TabularClassifier`. Any scikit-learn-style model pickled as `{model, features, name}` works. `training/tabpfn/evaluate.py` writes the TabPFN one.
- **Embeddings.** Change `retrieval.embedding_model`, then run `make docs-ingest` to re-embed.
