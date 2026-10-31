# Limitations (read before citing any number)

## Telemetry / TabPFN
- **Archival data, nine channels.** OPSSAT-AD covers 2,123 hand-selected segments from 9 channels, recorded January to June 2022. Results say nothing about other OPS-SAT subsystems or other spacecraft.
- **The paper has a split-count discrepancy.** Its text gives 1,494 training segments, but its own Table 1 and the released data give 1,594. We use the released data.
- **One test run per configuration.** The official test split was evaluated once per final configuration (`evaluations/test_run_log.jsonl`). The like-for-like base18 ablation is a separate, logged, post-hoc configuration that was not used for selection.
- **Engineered features help every model.** On our extended feature set, RF, XGBoost and LightGBM also exceed the published FCNN. TabPFN's edge over them there is small: a statistical tie with RF by McNemar, and AUPRC-difference CIs near zero. On the paper's 18 features alone, TabPFN's lead is clearer.
- **Published numbers are quoted, not reproduced.** We did not re-run FCNN or XGBOD. Those models used their own decision rules, while ours use thresholds chosen on training out-of-fold predictions.
- **MPS nondeterminism.** TabPFN on Apple MPS varies by about ±0.0002 CV AUPRC between runs.
- **The "top contributing characteristics" are approximate.** They combine global permutation importance with how far each feature deviates from the training median. They are not per-prediction SHAP values.

## Documents / retrieval
- **The archive is small.** There are 20 sources and 304 chunks. Most ESA material is stored as short excerpts because of its licence terms, so many questions honestly return "not in the archive".
- **The archive contains no per-segment incident reports.** For that reason the system never assigns a root cause to a specific segment.
- **The archive disagrees with itself in places, and we surface that rather than resolve it.** Examples:
  - Experiment counts and team countries differ between ESA sources.
  - The successor VOLT's launch is "late 2025" in a 2024 preprint and "2027" on Wikipedia.

## Mission Memory Interpreter (Tinker)
- **Task-A labels are programmatic.** Ground truth comes from a deterministic spec (`training/tinker/spec.py`): cue-based sentence selection, regex channels, dates and units, and a hedge-aware root-cause rule. "95% exact match" therefore means "95% agreement with this spec on held-out documents", not agreement with human annotators.
- **Field coverage is uneven.** In the held-out test passages, only a few contain channel IDs, units or operational responses. Per-field results for those fields rest on small counts (see `per_field` in `tinker_eval_A.json`).
- **Train-only augmentation.** Training uses real passages, re-chunked real passages, and templated passages built around real channel names. Validation includes some templated examples for iteration. **The test split is 100% real passages from held-out documents.**
- **Local inference is quantised.** It uses a Q4_K_M base with an f16 LoRA. `offline_inference.json` reports agreement with Tinker's full-precision outputs.
