# PROGRESS

Timestamps are IST (UTC+5:30). Deadline: 2026-10-31 23:59 PDT = 2026-11-01 12:29 IST.

## Decisions
- **Repo root** is `~/Desktop/wake ` itself (per the author's instruction). Note the trailing space in the folder name.
- **Python 3.11** venv via uv. `tabpfn` 9.2.0, `tinker` 0.36.0, `tinker-cookbook` 0.5.9, `torch` 2.15.0.
- **No HF token for now.** TabPFN uses the V2 checkpoint (Prior Labs License, i.e. Apache-2.0 + attribution). TabPFN-3/2.5 (gated, non-commercial) is added as a CV variant if a token becomes available.
- **Tinker base model: Qwen/Qwen3-8B.** It is the cheapest dense chat model on the 2026-10-19 price table, with train at $0.44/M tokens. Hard budget cap via `TINKER_BUDGET_USD`.
- **Local inference via llama.cpp** (Q4_K_M base + GGUF LoRA), because the machine has 18 GB RAM.

## Log
- 20:37 Scaffold, `git init`, `.env` / `.env.example`.
- 20:45 OPSSAT-AD downloaded. **md5 of both files matches Zenodo.**
- 20:50 Verification results:
  - 2,123 segments, 9 channels (matching the paper), anomaly rate 0.2044.
  - **The split is 1,594 train / 529 test.** The paper's text says 1,494 train, but its own class counts (1,273 + 321) sum to 1,594. The data agrees with 1,594.
- 20:55 Feature reproduction against `dataset.csv`:
  - 16/18 features match exactly.
  - `smooth10_n_peaks` differs on 3 of 2,123 segments and `smooth20_n_peaks` on 10 (edge cases at the peak-prominence threshold).
  - Overall agreement is 99.97%.
  - Bug found and fixed: the segments contain 22,115 duplicate timestamps, and re-sorting with a non-stable sort changed the diff-based features. We now keep file order.
- 21:05 SQLite built (303,493 telemetry points). API skeleton up. Frontend fixtures and `docs/ARCHITECTURE.md` written.
