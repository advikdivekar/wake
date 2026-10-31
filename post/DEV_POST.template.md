---
title: "The Last Satellite: giving a dead spacecraft a memory with TabPFN and Tinker"
published: false
tags: hacktoberfest, ai, opensource, machinelearning
---

*This is a submission for the [DEV Hacktoberfest Open-Source AI Challenge](https://dev.to/challenges), Week 4: Ghost in the Machine.*

> **Its mission ended. Its memories did not.**

## What I Built

OPS-SAT was ESA's "flying laboratory", a 30 cm CubeSat that strangers on the internet could program. It re-entered the atmosphere on **22 May 2024**. What remains is a ghost: thousands of archived telemetry fragments, a public anomaly dataset, and documents scattered across ESA pages, papers and news reprints that don't always agree with each other.

**The Last Satellite** is a *Mission Memory Engine* for that ghost. It is an archival investigation console with two models and one strict rule.

- **Telemetry Analyser (TabPFN).** It reads any of the {{data.segments}} archived segments from OPSSAT-AD (real magnetometer and photodiode telemetry). It estimates the probability that a segment is anomalous, shows which *measured* characteristics drive that estimate, and ranks segments in an investigation queue.
- **Mission Memory Interpreter (Qwen3-8B + LoRA trained on Tinker).** It turns mission documents into structured, source-linked records with eight fields: channel, sensor, units, event date, observation, operational response, root cause, evidence. Every text field must be a *verbatim* sentence from the source, and "unknown" is a first-class answer.
- **The strict rule.** The system never states a root cause unless a source explicitly says it. The archive contains no per-segment incident reports, so every investigation card says, honestly, *"Root cause of this signal behaviour is not documented in the archive."*

The two halves meet in **investigation cards**. Each statement on a card is either `[measured]` from the raw signal or `[cited]` from a document, and each card keeps separate lists of what is **known** and what is **not known**. An analyst can confirm, reject or investigate, and the feedback is stored. The hero demo, *"The signal that should not be there"*, hides a segment's label, walks through signal → features → probability → documentary memory → similar past segments → card, and only then **reveals** the truth. The demo set deliberately includes a false alarm and a missed anomaly.

## Demo

<!-- 60–90 s video + screenshots: see the checklist at the bottom of this file -->

## Code

{% github REPLACE_WITH_REPO %}

## How I Built It

### 1. Telemetry: reproduce first, then chase the published bar

- **Verified the data.** I downloaded OPSSAT-AD from Zenodo and verified the md5 of both files. Then I checked the counts myself: {{data.segments}} segments, {{data.points}} points, {{data.train}} train / {{data.test}} test, {{data.anomaly_rate}} anomalous. *Fun finding: the paper's text says 1,494 training segments, but its own Table 1 and the released data both say 1,594.*
- **Ported the published feature code.** It reproduces **{{feat.exact_count}}/18 features exactly** ({{feat.overall}} of values overall). Along the way I hit a classic bug. The raw file has 22,115 duplicate timestamps, so re-sorting with a non-stable sort silently changed the derivative features.
- **Selected everything on the training split only.** I used 5-fold grouped CV on train: feature-group ablations, then the TabPFN ensemble size. Thresholds come from out-of-fold predictions.
- **Ran the official test split once per final configuration,** logged in `test_run_log.jsonl`.

| Official test split ({{data.test}} segments) | AUCPR | F1 | MCC |
|---|---|---|---|
| **TabPFN-v2 + selected features** | **{{tab.auprc}}** [{{tab.auprc_ci}}] | **{{tab.f1}}** [{{tab.f1_ci}}] | **{{tab.mcc}}** |
| TabPFN-v2, *only the paper's 18 features* | {{abl.tabpfn-v2.auprc}} | {{abl.tabpfn-v2.f1}} | {{abl.tabpfn-v2.mcc}} |
| Random Forest (selected features) | {{base.rf.auprc}} | {{base.rf.f1}} | {{base.rf.mcc}} |
| XGBoost (selected features) | {{base.xgboost.auprc}} | {{base.xgboost.f1}} | {{base.xgboost.mcc}} |
| Isolation Forest (unsupervised) | {{base.iforest.auprc}} | {{base.iforest.f1}} | {{base.iforest.mcc}} |
| Best published (FCNN, *Sci Data* 2025) | 0.979 | 0.946 | 0.932 |

The final model made **{{tab.fp}} false alert(s) and {{tab.fn}} missed anomalies** across {{data.test}} archived segments. Its probabilities are well calibrated (Brier {{tab.brier}}), which matters because the probability drives the queue: *prioritise* at p ≥ {{thr.high}}, *queue* at p ≥ {{thr.low}}, *archive* below.

### 2. Documents: a small, licence-aware archive

- **Twenty public sources:** the OPSSAT-AD paper (fetched through the Europe PMC open-access API), the dataset README and code, Wikipedia, ESA pages, an ESA re-entry workshop deck, news reprints and an OPS-SAT experiment paper.
- **Licences decide what is stored.** Full text only for CC-BY, CC-BY-SA and MIT sources. Everything else gets ≤300-character excerpts and a link.
- **Hybrid retrieval:** SQLite FTS5 + local embeddings, fused with RRF. Every answer carries citations and a *"missing from the archive"* list.
- **Conflicts are surfaced, not resolved.** The archive disagrees with itself: one source says the successor mission VOLT launches in "late 2025", another says 2027, and ESA sources give different experiment counts.

### 3. Tinker: a small model that copies instead of inventing

- **Froze the metric first.** Before training anything I froze the headline metric: **field-level exact match on held-out documents**, scored on the raw output before any repair. It comes with valid-schema rate, verbatim-evidence rate, unsupported-root-cause count, Wilson CIs and a paired McNemar test against the base model.
- **Built the training set programmatically.** It comes from public OPS-SAT documents and the real channel catalogue. Each target is generated by a deterministic spec, every evidence excerpt is machine-checked as a substring, and hedged causes ("may have been…") must map to `?`.
- **Split by document family, not by chunk.** The test documents (the OPSSAT-AD paper + Wikipedia) never appear in training. The paper's arXiv preprint is excluded everywhere because it is a near-duplicate.
- **Chose a compact format.** Eight `field: value` lines, converted to Pydantic JSON in code. Loss is on the answer tokens only. LoRA rank 16 on **Qwen3-8B**, the cheapest dense chat model on Tinker's price list.

| Held-out test documents | Base Qwen3-8B | Fine-tuned | paired p |
|---|---|---|---|
| A. Record extraction, field exact match | {{tk.A.base}} | **{{tk.A.tuned}}** [{{tk.A.tuned_ci}}] | {{tk.A.p}} |
| B. Timeline (event vs publication date) | {{tk.B.base}} | {{tk.B.tuned}} | {{tk.B.p}} |
| C. Terminology with the correct citation | {{tk.C.base}} | {{tk.C.tuned}} | {{tk.C.p}} |
| D. Investigation note passes all checks | {{tk.D.base}} | {{tk.D.tuned}} | {{tk.D.p}} |

The fine-tuned model reaches a valid schema on {{tk.A.tuned.valid_schema_rate}} of outputs, keeps evidence verbatim {{tk.A.tuned.evidence_fidelity}} of the time, and produces **{{tk.A.tuned.unsupported_root_causes}} unsupported root causes**. **Total Tinker spend: {{tk.cost_total}}** (token counts × list price, logged before every job by a budget guard).

**Did I hit 95%? No.** The fine-tuned model scores {{tk.A.tuned}} on held-out test documents ({{lc.final}} on validation). The gains are real, though:
- Channel IDs: 100% correct.
- Evidence: copied verbatim every time.
- Whole records exactly right: 0% → {{tk.A.tuned.record_exact_match}}.

What's left is the hard part: choosing *which* sentence is "the observation" in an unfamiliar document.

**Offline.** Training happened on Tinker's hosted service. Tinker doesn't let you download *sampler* checkpoints, which is all my final run had saved. So I retrained the 200-example configuration with a downloadable checkpoint (validation {{lc.offline}} vs {{lc.final}} for the final model). I converted it to GGUF and now run it **locally** with llama.cpp on a laptop (Q4_K_M base + LoRA), with no Tinker key in the environment. On held-out passages it scores {{off.em}} and agrees with the same adapter's full-precision Tinker outputs on {{off.agree}} of fields, at {{off.sec}} s per passage.

### What went wrong (honestly)

- **My first base-model comparison was unfair.** My prompt never named the eight fields and my parser rejected markdown, so the base model looked worse than it is. I fixed both *before* training anything, using validation outputs only.
- **Validation error analysis found bugs in my labels, not in the model.** The first labelling rules picked code blocks and footnotes as "observations", and the model was right to refuse them. I tightened the spec to prose-only sentences, stopped a half-finished training run to save budget, and retrained once.
- **A 100-example model collapsed on investigation notes.** With greedy decoding it repeated the same bullet until it ran out of tokens. More task-D examples fixed it at 200.
- **Fine-tuning made one task worse.** Terminology answers with the correct citation dropped from {{tk.C.base}} to {{tk.C.tuned}} (paired p = {{tk.C.p}}). That task had only 32 training examples, and the tuned model learned to answer "not in archive" too eagerly.
- **The headline target was missed.** {{tk.A.tuned}} on test vs the 95% I set before training. I'm reporting it as measured.
- **I saved the wrong kind of checkpoint.** Sampler weights can't be downloaded, so the adapter in the offline demo is the 200-example sibling of the evaluated model.
- **TabPFN and XGBoost segfault on macOS when loaded in the same process** (two OpenMP runtimes), so the pipeline runs them as separate stages.
- **On my engineered features, Random Forest is a statistical tie with TabPFN** (McNemar p = {{sig.rf.p}}). TabPFN's clearer win is on the paper's own 18 features, where it needs no feature engineering at all.

### Limitations

- **Narrow coverage.** This covers nine channels and 2,123 hand-picked segments from early 2022, so it says nothing about other subsystems.
- **Task-A ground truth is a deterministic spec, not human annotation.** "Exact match" means agreement with that spec on unseen documents. Some fields (channel IDs, units) appear in only a handful of held-out passages.
- **Published numbers are quoted, not re-run.** Their decision rules differ from our out-of-fold thresholds.
- **Local inference is quantised** (Q4_K_M).

### Licensing nuance

- **OPSSAT-AD:** CC-BY-4.0. The prompt I started from said MIT; the Zenodo record says otherwise.
- **Feature code:** MIT.
- **TabPFN:** all reported results use the **v2 weights (Prior Labs License, Apache-2.0 + attribution)**. The newer TabPFN-2.5/3 checkpoints are non-commercial, gated, and were not used.
- **Qwen3-8B:** Apache-2.0.
- **ESA material:** stored only as short excerpts and links.

## Why Does Open Innovation Matter?

OPS-SAT existed because ESA let outsiders upload experiments to a satellite. After it burned up, its telemetry survives only because the dataset authors published it openly, with code that let me reproduce their features to the last decimal and catch a typo in their split count. Every layer of this project depends on that openness: open data, an open benchmark to beat, open weights I can run on a laptop, and a hosted trainer that hands me back my adapter. The ghost in the machine is the archive itself. If it stays open, anyone can keep questioning it after the people who flew the mission have moved on.

## My Agent Session

<!-- Paste session highlights / link here -->

## The Spirit of It

A memorial should be honest. The console uses marigold and candlelight rather than horror. It treats a false alarm as part of the record, and it would rather say *"not documented in the archive"* than invent a story about why a dead satellite's sensor went quiet.

## Prize Categories

- **Best Use of Tinker.**
  - LoRA SFT of Qwen3-8B on a frozen, programmatically verified extraction spec.
  - Split by document, with a learning curve and per-run cost.
  - Base vs tuned with paired statistics.
  - A sibling adapter downloaded and run fully offline.
  - Honest misses: 95% target not reached ({{tk.A.tuned}}), and task C regressed.
  - Total spend {{tk.cost_total}}.
- **Best Use of TabPFN.**
  - TabPFN-v2 beats the best published OPSSAT-AD result on the official test split: AUCPR {{tab.auprc}} vs 0.979, F1 {{tab.f1}} vs 0.946.
  - It even does so on the paper's own 18 features ({{abl.tabpfn-v2.auprc}} / {{abl.tabpfn-v2.f1}}).
  - It is calibrated, explained, and compared against five baselines with bootstrap CIs and McNemar tests.

---

### Demo script (60–90 s)

1. **0–10 s.** Mission Archive: "OPS-SAT re-entered on 22 May 2024. This is what it left behind." Scroll the last-transmission timeline.
2. **10–25 s.** Signal Observatory: a magnetometer channel with zero runs and gaps highlighted.
3. **25–55 s.** Guided demo, *The signal that should not be there*: hidden label → features → TabPFN probability → cited documents → similar past segments → card with the KNOWN / NOT KNOWN lists → **Reveal**.
4. **55–70 s.** Show the false positive and the missed anomaly from the demo set.
5. **70–85 s.** Mission Memory: ask "Why did OPS-SAT re-enter early?" and show the citations plus the *missing from the archive* list. Then show the Model Laboratory tables.
6. **85–90 s.** Show the terminal running the adapter offline with llama.cpp.

### Screenshot checklist

- [ ] Mission Archive with the timeline
- [ ] Signal Observatory (zero runs + gaps)
- [ ] Investigation card with known / not known
- [ ] Reveal moment, a TP and the FN
- [ ] Mission Memory answer with citations
- [ ] Model Laboratory: ours vs published, PR curve, calibration
- [ ] Tinker base vs tuned table + learning curve
- [ ] Terminal: offline llama.cpp inference
