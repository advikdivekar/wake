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
- 21:10 TabPFN CV moved to MPS. TabPFN refuses CPU above 1,000 samples, and MPS is faster with identical AUPRC. Run-to-run MPS nondeterminism is about ±0.0002 AUPRC.
- 21:20 **Bug: torch and xgboost/lightgbm OpenMP runtimes clash in one process** (segfault 139 / OMP Error #179). Fix: TabPFN and tree baselines now run as separate subprocess stages (train.py / evaluate.py `--stage`).
- 21:25 PMC returned 403 to scripted fetches. Fetched via the official Europe PMC REST full-text API instead (no bot circumvention). Tables 3 and 4 of the paper were re-verified programmatically from the JATS XML.
- 21:30 Document archive: 20 sources, 304 chunks. Full text only for CC-BY / CC-BY-SA / MIT sources; ESA and publisher pages keep excerpts of 300 characters or fewer. All 11 timeline entries are verified as verbatim quotes.
- 21:45 CV selection (train only):
  - Feature groups zeros_gaps, autocorr and robust each improved CV AUPRC; spectral and channel did not.
  - The combination of the three groups is best.
  - n_estimators=8 is best (CV AUPRC 0.9781).
- 21:50 Thresholds from training OOF: max-F1 0.617, high 0.80 (precision ≥ 0.95), low 0.05 (recall ≥ 0.98).
- 21:55 **ONE official test run** (logged in `test_run_log.jsonl`):
  - TabPFN-v2: AUPRC 0.996, F1 0.982, MCC 0.977. Published FCNN: 0.979 / 0.946 / 0.932.
  - Confusion matrix: 1 FP, 3 FN.
  - Baselines on our features are close: RF 0.994, XGB 0.993, LGBM 0.990. Against RF the result is a statistical tie.
- 22:25 **Base Qwen3-8B on VAL (local, before any fine-tuning):** task A field exact match 0.593, valid-schema rate 0.0, task D sections 0.0.
  - Inspection showed two unfair setup issues: the system prompt never named the 8 fields, and the parsers rejected markdown (`**KNOWN**`).
  - **Amendments, made before any tuned model existed and with TEST untouched:**
    1. The system prompt now lists the fields explicitly. Base and tuned get the same prompt.
    2. The parsers strip markdown bullets, bold and headings for both models.
    3. Task-D gold citations now use the same prose-only sentence filter as the cards.
  - Re-running the base on VAL with the amended prompt.
- 23:05 Tinker key verified; Qwen/Qwen3-8B is in the catalogue. Balance $0.93, so the cap is set to $0.75.
- 23:10 Smoke run lc-n50: NLL fell from 0.76 to 0.05, checkpoints saved, sampling OK.
- 23:15 Learning curve, VAL (spec v1 labels), task A field exact match. Base is 0.673 (local).
  - n50: 0.885
  - n100: 0.892. Task D collapsed to 0.0 because of greedy repetition loops, with only about 9 D training examples.
  - n200: 0.895. Task D recovered to 0.733.
- 23:30 **VAL error analysis:** most remaining task-A "errors" were defective gold labels. The v1 cue rules selected code blocks, footnotes and markdown bullet lists as "observation"/"evidence" sentences.
  - **Spec v2:** text fields only accept prose sentences (`spec.is_prose`). The prompt says so. Bullet lists are split into sentences.
  - Stopped the v1 full run at step 65/84 to save budget (pro-rata cost added to the ledger).
  - Retraining once as `final-v2`. TEST is still untouched.
  - The v1 learning-curve points are kept and labelled as trained on v1 labels.
- 23:55 final-v2 (445 examples, spec v2), task A field exact match on VAL: 0.930. Task D: 1.0.
- 00:05 **ONE TEST run** (Tinker backend, base vs tuned, guarded and logged), base → tuned:
  - Task A: 0.722 → 0.863 (p = 6e-16). The 95% target was NOT reached.
  - Task B: 0.375 → 0.542 (p = 0.125).
  - Task C: 0.962 → 0.827, a regression (p = 0.016).
  - Task D: 0.56 → 1.0 (p = 0.001).
  - Unsupported root causes: 0 for both models.
- 00:10 **Sampler checkpoints cannot be downloaded** (CLI, cookbook and load_state all refuse).
  - The author chose option 2: retrain the n200 config with `save_state` (`offline-n200-v2`, VAL 0.923).
  - Conversion path: PEFT export (`unembed_tokens` renamed to `lm_head`), llama.cpp `convert_lora_to_gguf` (b11669), `models/adapter.gguf`.
  - Offline run (llama.cpp, no Tinker key, HF offline): VAL 0.925, with 100% field agreement with the same checkpoint's Tinker outputs.
- 00:15 The app interpreter backend is now `llamacpp` (local adapter). Runtime extraction falls back to the regex reading for flagged channel and date fields. Estimated Tinker total: $0.83.
- 01:00 (1 Nov IST) **Web console (`web/`)** built: Vite, React, react-three-fiber, Lenis and Framer Motion.
  - Live API mode, with a labelled snapshot fallback that holds real API responses (`scripts/export_snapshot.py`).
  - Visually QA'd in real Chrome at desktop and mobile widths with `web/shoot.mjs` and `web/shoot_mobile.mjs`.
  - QA fixes: gaps no longer drawn on downsampled channel views; the Q&A missing-list shows real words instead of stems; a reverted ranking hack that had broken the "cause unknown" guard.
- 01:20 The DEV post is written at `dev/the-last-satellite.md`. Every number was re-checked against `evaluations/`.
- 01:25 The GitHub repo was renamed to `advikdivekar/wake` (public) by the author.
  - Pushes after the rename were blocked by the agent's permission classifier, so the author pushes.
  - The Pages workflow was not added (blocked as a new public surface).
