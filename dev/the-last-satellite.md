---
title: "A dead satellite, read twice: TabPFN beat the published OPS-SAT benchmark out of the box, and an 83-cent Tinker LoRA learned to say 'not documented in the archive'"
published: false
tags: devchallenge, hf26challenge, tinker, ai
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges)*

> **MISSION LOG · OPS-SAT · 22 May 2024**
> Signal lost. Re-entry over the night of 22–23 May, after four and a half years in orbit.
> *What remains: 2,123 archived telemetry fragments, a public anomaly dataset, and twenty documents that don't always agree with each other.*

OPS-SAT was ESA's flying laboratory: a CubeSat that strangers could upload code to. ESA's mission-end coverage says it was "impacted by the recent unexpectedly strong increase in solar activity that began in early 2024". It burned up on **22 May 2024**.

A ghost in the machine is usually a story. This one is a dataset. I built **The Last Satellite**, a *Mission Memory Engine* that reads what OPS-SAT left behind, and is honest about what it cannot know.

## What You're About to Read

- **TabPFN vs the paper.** On the **official OPSSAT-AD test split** (529 segments, run once, logged), TabPFN-v2 scored **AUCPR 0.996, F1 0.982, MCC 0.977**. The best published model (an FCNN in *Scientific Data*, 2025) scored 0.979 / 0.946 / 0.932.
  - **Even on the paper's own 18 features, with no feature engineering at all**, TabPFN reached 0.989 / 0.950 / 0.937.
  - That's **1 false alarm and 3 missed anomalies** in 529 archived segments.
- **Tinker for 83 cents.** A Tinker LoRA on **Qwen3-8B** took structured record extraction on held-out documents from **72.2% to 86.3%** field-level exact match (paired p = 6×10⁻¹⁶).
  - **Evidence copied verbatim 100% of the time** (base: 81%), and **0 unsupported root causes**.
  - Investigation notes passing every automated check went from **56% to 100%**.
  - **$0.83 for everything on Tinker**: every training run, the learning curve, a run I killed on purpose, and every evaluation.
- **The design rule.** Every statement on screen is either `[measured]` from the raw signal or `[cited]` from a document. A root cause is never asserted unless a source states it, and the archive has no per-segment incident reports. So, honestly: *"Root cause of this signal behaviour is not documented in the archive."*
- **Offline.** I downloaded an adapter and ran it locally with llama.cpp on an 18 GB laptop, with no network and no API key. It agrees **100% field-for-field** with the same checkpoint sampled on Tinker.
- **What I missed, measured and not hidden.** I set a 95% target before training. I got **86.3% on test**. One task got *worse* after fine-tuning. Both are in the tables below.

## What I Built

**The Last Satellite** is an archival investigation console with two open models, one evidence layer and one rule.

| | Model | Job |
|---|---|---|
| 📡 **Telemetry Analyser** | **TabPFN-v2** | Reads each archived telemetry segment and estimates P(anomalous). It explains which *measured* characteristics drive that estimate and ranks all 529 test segments into *prioritise / queue / archive*. |
| 📜 **Mission Memory Interpreter** | **Qwen3-8B + LoRA trained on Tinker** | Turns mission documents into 8-field, source-linked records, reconstructs timelines, explains telemetry terms with citations, and writes investigation notes split into **KNOWN** and **NOT KNOWN**. |
| 🕯️ **Evidence layer** | plain, tested code | Measures zero runs, gaps and peaks. Retrieves documents (SQLite FTS5 + local embeddings). Finds similar historical segments ("resemblance, not a shared fault"). Then validates everything the language model says. |

The console is a single scroll from orbit to re-entry:

- **Elegy.** A "last transmission" timeline. Every entry is a verbatim quote, checked against the stored source before it may appear. Event dates and publication dates are kept apart.
- **Signal Observatory.** All nine instruments (3 magnetometers, 6 photodiodes), drawn exactly as archived. Zero runs glow ember; gaps are dark voids.
- **The signal that should not be there.** Pick one of six candles: real test segments with their labels hidden. Step through signal → features → TabPFN probability → documentary memory → similar past segments → investigation card, then **reveal the truth**. The six include the false alarm and an anomaly the model missed. A memorial should be honest.
- **Investigation Queue.** 529 segments ranked by probability. Open one, read its card, and **Confirm / Reject / Investigate**. The verdict is stored as feedback.
- **Mission Memory.** Ask the archive. Answers carry citations, and a separate panel lists **what is missing from the archive** instead of filling the gap with a guess.
- **Model Laboratory.** Every chart is read from the evaluation files the pipeline wrote. Nothing is typed in by hand.

Behind it is a shader-lit Earth whose city lights burn like candles. As you scroll, a tiny CubeSat's orbit decays, the planet warms to marigold, and the satellite streaks in. A restrained *ofrenda*, not a horror movie.

## Demo

{% embed REPLACE_WITH_VIDEO_URL %}

<!-- Screenshots: hero · guided demo reveal (TRUE POSITIVE / MISSED ANOMALY) · investigation card KNOWN vs NOT KNOWN · Mission Memory "missing from the archive" · laboratory vs published bar · Tinker learning curve · terminal running the adapter offline -->

What to try:

1. **The Signal → pick a candle → ▶ guided.** Watch the ring fill to TabPFN's probability, then hit **Reveal the truth**. Try segment **#1579**: it's the anomaly the model missed, and the console shows it.
2. **Queue → open #204.** A 16-sample run of exact zeros, P = 1.000, *prioritise*. Then read the NOT KNOWN column.
3. **Mission Memory → "What caused the zero values on the magnetometer channels?"** The archive doesn't know, and says so.
4. **Laboratory → toggle "18 published features".** That's the like-for-like comparison with the paper.

The console talks to the FastAPI backend when it's running. Without it, it falls back to a labelled **archived snapshot** of *real* API responses, so it works anywhere.

## Code

{% github advikdivekar/wake %}

`make setup data features db docs-ingest tabpfn-cv tabpfn-test && make app` reproduces the TabPFN side. The Tinker steps need a key and are budget-guarded. The web console is `cd web && npm run dev`. The repo is MIT; the data and models keep their own licences (see below).

## How I Built It

### The rule behind all of it: measure, cite, or say "unknown"

A language model is a wonderful reader and a terrible witness. So each job goes to whatever can actually be held accountable for it:

- **TabPFN** owns the numbers about signals.
- **Plain code** owns every measurement: zero runs, gaps, peaks, thresholds.
- **The fine-tuned model** only reads and writes, and its output passes through a validator before it reaches the screen:
  - every quoted sentence must exist **verbatim** in the source;
  - channel IDs and dates are cross-checked by an **independent regex reader** that never saw the model;
  - any "root cause" must be stated, unhedged, by a cited source.

### Part 1: TabPFN vs the published benchmark

#### First, reproduce the paper

I downloaded OPSSAT-AD from Zenodo, md5-verified both files, and counted for myself:
- 2,123 segments and 303,493 telemetry points;
- 9 channels;
- 20.4% anomalous;
- 1,594 train and 529 test segments.

*Small find: the paper's text says 1,494 training segments, but its own Table 1 and the released data both say 1,594.*

Then I ported the published feature code. It reproduces **16 of the 18 features exactly** (99.97% of all values). Along the way it caught a nasty bug: the raw file has **22,115 duplicate timestamps**, so a non-stable sort silently changed every derivative feature. The bug was mine, and the fix is to keep file order.

#### The bar

These are the published results, re-verified programmatically against the paper's full text (Ruszczak et al., *Sci Data* 2025, Table 3, official test split):

| Published | AUCPR | F1 | MCC |
|---|---|---|---|
| FCNN (best supervised) | 0.979 | 0.946 | 0.932 |
| XGBOD | 0.975 | 0.918 | 0.897 |
| MO-GAAL (best unsupervised) | 0.779 | 0.726 | 0.710 |

#### Everything chosen on training data only

All selection used 5-fold grouped CV on the **training split**, where neighbouring segments of a channel never straddle folds:
1. **Feature groups.** I tested candidate groups one at a time and kept the ones that raised CV AUPRC: zero/gap statistics (0.9714), autocorrelation (0.9723) and robust spread (0.9752), against 0.9704 for the 18 published features alone. Spectral features and channel identity didn't help, so they were dropped.
2. **Ensemble size.** I chose 8 estimators (CV AUPRC 0.9781).
3. **Thresholds.** These come from **training out-of-fold** predictions:
   - max-F1 at 0.617;
   - *prioritise* at ≥ 0.80, where precision is ≥ 0.95;
   - *queue* at ≥ 0.05, where recall is ≥ 0.98.

Then I ran the official test split **once**. A guard logs every test run and refuses to run the same configuration twice.

#### Checked before trusted

| Official test split (529) | AUCPR | F1 | MCC |
|---|---|---|---|
| **TabPFN-v2 (selected features)** | **0.996** [0.989–1.000] | **0.982** [0.963–0.996] | **0.977** |
| Random Forest (same features) | 0.994 | 0.973 | 0.966 |
| XGBoost (same features) | 0.993 | 0.968 | 0.960 |
| LightGBM (same features) | 0.990 | 0.969 | 0.960 |
| Logistic regression (same features) | 0.987 | 0.956 | 0.944 |
| Isolation Forest (unsupervised) | 0.401 | 0.499 | 0.362 |
| "Lots of zeros or a gap" rule | 0.293 | 0.527 | 0.414 |
| *FCNN, best published* | *0.979* | *0.946* | *0.932* |

Brackets are 95% bootstrap CIs.

**A win, but on my features not a thrashing.** Feature engineering lifts every model, and against Random Forest TabPFN is a statistical tie (McNemar p = 0.63; AUPRC difference +0.002, 95% CI −0.0005 to +0.006). Against LightGBM and XGBoost the AUPRC-difference CIs sit just above zero, and against logistic regression TabPFN wins with p = 0.03.

So I ran the comparison the paper actually made: **only the 18 published features, no engineering.** It's a separate configuration, run once and logged, and not used for any decision.

| Paper's 18 features only | AUCPR | F1 | MCC |
|---|---|---|---|
| **TabPFN-v2** | **0.989** | **0.950** | **0.937** |
| Random Forest | 0.970 | 0.920 | 0.903 |
| XGBoost | 0.970 | 0.917 | 0.897 |
| LightGBM | 0.968 | 0.907 | 0.885 |
| *FCNN, best published* | *0.979* | *0.946* | *0.932* |

That's the result I'm proudest of. With the paper's features, an out-of-the-box tabular foundation model beats the tuned tree ensembles by ~0.02 AUCPR, and edges past the best published neural network with no training loop.

**It also has to be calibrated**, because the probability *is* the investigation queue. The Brier score on test is **0.0073**, and the reliability curve hugs the diagonal. A "missed anomalies vs false alerts" slider in the lab lets you pick your own trade-off from the out-of-fold curve.

#### Things I got wrong first

- **TabPFN refused to run on CPU** with more than 1,000 training rows. Apple's MPS backend was faster anyway, with identical AUPRC.
- **TabPFN and XGBoost segfault when loaded in the same process** on macOS, because two OpenMP runtimes collide (exit 139). Now they run as separate pipeline stages.
- **The newest TabPFN weights are gated and non-commercial.** I used **TabPFN v2**, which downloads without an account and is Apache-2.0 + attribution. Every result above is v2.
- **My first observatory plot drew 553 "gaps"** that were really just artefacts of downsampling. Gaps are now only computed on raw samples.

### Part 2: Tinker, a small model taught to copy instead of invent

#### 1. Freeze the metric before you train

Before any model saw any data, I froze the headline metric: **field-level exact match** on held-out documents, scored on raw output *before* any repair. Companion metrics:
- valid-schema rate;
- verbatim-evidence rate;
- unsupported-root-cause count;
- correct use of "unknown";
- Wilson CIs;
- a paired McNemar test against the base model.

#### 2. Shrink the bill before you shrink the model

Tinker bills per token, so the output is 8 compact lines, not JSON:

```
channel_id: CADC0873
sensor_type: magnetometer
units: ?
event_date: 2024-05-22
observation: On 22 May 2024 the magnetometer I_B_FB_MM_1 reported a run of zero values.
operational_response: ?
root_cause: ?
evidence: On 22 May 2024 the magnetometer I_B_FB_MM_1 reported a run of zero values.
```

Code converts it to Pydantic JSON. A full training example, prompt and passage included, averages **about 380 tokens**.

I priced the options from Tinker's list (training per 1M tokens):
- **Qwen3-8B: $0.44.**
- Qwen3.5-4B: $0.737. Smaller is not cheaper.
- GPT-OSS-20B: $0.396, but its thinking tokens would cost more at sampling time and break the format.

I picked Qwen3-8B with thinking disabled.

#### 3. Data: split by document, verify every excerpt

- **Programmatic targets.** They're built from public OPS-SAT documents and the real channel catalogue, using a deterministic spec:
  - cue-based sentence selection;
  - regex channels, dates and units;
  - a hedge-aware cause rule, so "may have been caused by…" maps to `?`.
- **Split by document family, never by chunk.** The test set is the OPSSAT-AD paper (the only real source that names channels) plus Wikipedia, so it's 100% real, held-out passages. The paper's arXiv preprint is **excluded everywhere** because it's a near-duplicate.
- **Size:** 445 training examples across four tasks.

#### 4. Train: rank-16 LoRA, loss on the answer only

```python
renderer = renderers.get_renderer("qwen3_disable_thinking", tok)
mi, w = renderer.build_supervised_example(messages, train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE)
fb = tc.forward_backward(batch, loss_fn="cross_entropy")
op = tc.optim_step(tinker.AdamParams(learning_rate=lr_t, beta1=0.9, beta2=0.95, eps=1e-8))
```

- **Schedule:** 3 epochs, batch 16, linear LR decay, a checkpoint every epoch. The final run took **5.1 minutes**.
- **Budget guard:** it prices every job from local token counts *before* submitting and refuses anything over the cap. That mattered: I started with **$0.93** of credit.

#### 5. Find the knee (validation, task A)

| Training examples | Cost | Field exact match |
|---|---|---|
| 0 (base Qwen3-8B) | n/a | 65.3% |
| 50 | $0.025 | 90.8% |
| 100 | $0.049 | 91.8% |
| 200 | $0.097 | 92.2% |
| 445 (final) | $0.224 | **93.0%** |

**Two and a half cents buys +25 points.** After that, every doubling of the data buys about one more point.

#### 6. Error analysis on validation found *my* bugs, not the model's

At 200 examples, most remaining "errors" were the model **correctly refusing** to quote code blocks, footnotes and markdown bullet lists that my labelling rules had picked as "observations".
- I tightened the spec to prose-only sentences (v2).
- I **killed a half-finished training run** rather than pay to finish it on bad labels.
- I retrained once. The test set was never touched until the end.

#### 7. The one test run

Held-out documents, same prompt, same parser, same validator:

| Task | Base Qwen3-8B | + Tinker LoRA | paired p |
|---|---|---|---|
| **A.** Record extraction, field exact match | 72.2% | **86.3%** [83.2–88.9] | 6×10⁻¹⁶ |
| **B.** Timeline: event vs publication dates | 37.5% | 54.2% | 0.13 |
| **C.** Terminology with the correct citation | **96.2%** | 82.7% | 0.016 |
| **D.** Investigation note passes all checks | 56% | **100%** | 0.001 |

| Task A detail | Base | Tuned |
|---|---|---|
| Channel IDs correct | 70.8% | **100%** |
| Evidence copied verbatim from the source | 81.1% | **100%** |
| "Unknown" used correctly | 82.1% | **99.8%** |
| Whole record exactly right | 0% | **44.4%** |
| Errors caught by the independent validator | 40 | **0** |
| Unsupported root causes | 0 | 0 |

The base model's 40 validator catches are the point of the validator: they're channel IDs and quotes it made up. **The fine-tuned model stopped making the kind of mistake the validator exists to catch.** Even after the validator repairs the base model's output, it reaches 78.5%, still below the fine-tune's *unrepaired* 86.3%.

#### 8. Rent the training. Keep the weights.

Training ran on Tinker; inference runs on my laptop:
- I exported the adapter as PEFT and renamed one tensor (`unembed_tokens` → `lm_head`).
- llama.cpp converted it to GGUF.
- It runs over a Q4_K_M Qwen3-8B base with `--lora`, with no Tinker key in the environment and Hugging Face offline.

Result: **92.5%** field exact match on held-out passages, **100% agreement** with the same checkpoint's full-precision Tinker outputs, at **4.7 s per passage** on an M3 Pro.

#### The whole bill

| Item | Est. cost |
|---|---|
| Learning-curve runs (50 / 100 / 200) | $0.17 |
| A run I stopped at 65/84 steps after finding label bugs | $0.17 |
| Final model (445 examples, 3 epochs) | $0.22 |
| Downloadable sibling adapter (see below) | $0.10 |
| All evaluation on Tinker (5 val passes + base & tuned on test) | $0.17 |
| **Everything on Tinker** | **$0.83** |

Costs are token counts × Tinker's list price, logged before every job. Base-model validation ran locally for free.

### Known edges (measured, not hidden)

- **I missed my own target.** I set **95%** before training. The model got **93.0% on validation** and **86.3% on test**. Most of the gap is one judgement call: *which* sentence counts as "the observation" in an unfamiliar document.
- **Fine-tuning made one task worse.** Citing the right source for a telemetry term fell from 96.2% to 82.7%. That task had only 32 training examples, and the tuned model learned to answer "not in the archive" too eagerly.
- **The offline adapter is a sibling, not the evaluated model.** Tinker doesn't let you download *sampler* checkpoints, which is all my final run had saved. So the offline adapter is the 200-example configuration, retrained with a downloadable checkpoint (validation 92.3% vs 93.0%). The training script now saves both kinds.
- **The labels are a spec.** Task-A ground truth comes from a deterministic spec, not human annotation, so "exact match" means agreement with that spec on unseen documents. Some fields (units, operational responses) appear in only a handful of held-out passages.
- **The validator rejects my own model.** In the live demo, 4 of the 6 investigation cards fell back to the deterministic template. In one, the interpreter wrote that "the root cause … *is documented*" under KNOWN, which contradicts its own UNKNOWN section. The guard caught it. I'd rather show a plain card than a confident wrong one.
- **The archive retriever is simple.** Ask "why did OPS-SAT re-enter early?" and it returns the launch date plus "no archived source states a cause". The archive *does* contain a sentence about solar activity. I tried a ranking hack to surface it, watched it break the "cause unknown" guard for other questions, and reverted it.

## Why Does Open Innovation Matter?

- **Only open data can be audited.** OPS-SAT existed because ESA opened a satellite to outsiders. After it burned up, its telemetry survives only because the dataset authors published it openly, with the code that let me reproduce their features to the last decimal, and catch a typo in their split.
- **Open weights let me change the model, not just the prompt.** Base Qwen3-8B invented channel IDs. Eighty-three cents of LoRA training stopped that. With a closed API I'd be writing longer prompts and hoping.
- **The weights are mine to keep.** The adapter runs on the laptop that holds the archive. No meter is running, and nobody can deprecate it before the next mission.
- **Calibration can be checked.** With TabPFN's weights and the public test split, I could measure calibration myself (Brier 0.0073) instead of trusting a probability someone else printed.
- **Memory should be a commons.** A mission's memory shouldn't live behind someone else's API key. The export button bundles documents, records, cards, feedback and every evaluation into one archive you can carry out.

## My Agent Session

I built this with **Claude Code** as a pair, from a written 12-hour plan with a cost estimate up front. A few moments worth recording:

- **It read the sources before writing code.** It pulled the paper's full results table and re-verified it against the JATS full text. It also read the original feature code before porting it.
- **It built guards before it needed them:**
  - a test-set guard that refuses a second run of the same configuration;
  - a budget guard that prices every Tinker job before submitting;
  - a ledger, updated by hand when it killed a run mid-way.
- **It caught its own mistakes:**
  - a duplicate-timestamp sort bug;
  - an unfair base-model prompt, fixed *before* training;
  - label defects found through validation error analysis;
  - a root-cause rule that briefly treated "*due to* the underlying nature of the mission" as a cause.
- **It stopped spending when the data said to.** It killed a half-finished run on bad labels, and when it lost the downloadable checkpoint, it asked me before spending the last of my credit.
- **It reverted its own "improvement".** The Q&A ranking hack made one answer look better and the honesty guarantees worse, so it went.

## The Spirit of It

A memorial should be honest. The console uses marigold and candlelight rather than horror. It keeps the false alarm and the missed anomaly in the record, and it would rather say ***"not documented in the archive"*** than invent a story about why a dead satellite's sensor went quiet.

## Prize Categories

**Best Use of TabPFN.** TabPFN is the engine of the console, not a bolt-on: every probability, every queue position and every "top measured characteristic" comes from it.
- **Official OPSSAT-AD test split, one logged run:** AUCPR **0.996**, F1 **0.982**, MCC **0.977**, against the best published 0.979 / 0.946 / 0.932.
- **On the paper's own 18 features, out of the box:** 0.989 / 0.950 / 0.937, beating tuned RF, XGBoost and LightGBM by ~0.02 AUCPR.
- **Rigour:** calibrated (Brier 0.0073), with thresholds chosen on training data only, and compared against five baselines with bootstrap CIs and McNemar tests, including the tie I lost the bragging rights to.

**Best Use of Tinker.** LoRA SFT of Qwen3-8B with loss on answers only, per-epoch checkpoints, a learning curve with per-run cost, a budget guard, and paired base-vs-tuned statistics on held-out documents.
- **Task A:** 72.2% → **86.3%** (p = 6×10⁻¹⁶).
- **Verbatim evidence:** 81% → **100%**.
- **Investigation notes:** 56% → **100%**.
- **0 unsupported root causes.**
- **The adapter runs fully offline**, agreeing 100% with Tinker.
- **$0.83** for everything, honest misses included.

---

*Built solo, with Claude Code, over one long Halloween night.*

*Two models. Eighty-three cents of training. One rule: measure it, cite it, or call it unknown. If that sounds like the right way to remember a satellite, a ❤️ or 🦄 helps more people find it.*
