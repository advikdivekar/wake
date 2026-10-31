---
title: "A dead satellite left 2,123 signals. TabPFN beat the published benchmark with no training loop, and 83¢ of Tinker taught an LLM to say 'unknown'"
published: false
tags: tinker, hf26challenge, devchallenge, hacktoberfest
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges)*

**Segment 1579. Photodiode I_PD3_THETA. 2 June 2022, 03:15:08 UTC.**

Thirty-one samples. A soft hump of sunlight, then the signal drops to **exactly zero** for two readings.

My model looked at it and said **0.098**. Probably fine. Let it rest in the archive.

**It was an anomaly.**

The spacecraft that sent it, ESA's OPS-SAT, burned up in the atmosphere on **22 May 2024**. There is nobody left to radio. Its engineers have moved on. What remains is a public dataset, twenty documents that don't always agree with each other, and the question every ghost story asks: *what happened here?*

**The Last Satellite** listens to that archive with two open models. It ranks every archived signal by how wrong it looks and reads the mission's documents for context. When you ask *why* a sensor went quiet, it says **"Root cause of this signal behaviour is not documented in the archive."** It says that because it's true. And it keeps segment 1579, the one it missed, **on the front page**.

{% embed REPLACE_WITH_VIDEO_URL %}

## What You're About to Read

- **The TabPFN result:** on the **official OPSSAT-AD test split** (529 segments, run exactly once, logged), TabPFN-v2 scored **AUCPR 0.996, F1 0.982, MCC 0.977**. The best published model (an FCNN in *Scientific Data*, 2025) scored **0.979 / 0.946 / 0.932**.
- **The same features as the paper, no training loop:** using only the paper's 18 features, TabPFN still beats it: **0.989 / 0.950 / 0.937**. It also beats my tuned Random Forest, XGBoost and LightGBM by about **0.02 AUCPR**.
- **The Tinker result:** one LoRA on Qwen3-8B took structured extraction from mission documents from **65.3% to 93.0%** field-level exact match (validation), **for 83 cents all-in**. On fully held-out test documents it went from **72.2% to 86.3%** (paired p = 6×10⁻¹⁶).
  - Evidence copied verbatim: **81% → 100%**.
  - Investigation notes passing every automated check: **56% → 100%**.
- **The cost:** **$0.22** for the final model. **$0.83 for everything on Tinker**: every run, the learning curve, a run I killed on purpose, and every evaluation.
- **The honesty record:** **1 false alarm and 3 missed anomalies** in 529 segments, all shown in the demo, and **0 invented root causes** from either model. I also show where I **missed my own 95% target**, and the one task fine-tuning made **worse**.
- **You keep it:** the adapter runs **offline** on a laptop through llama.cpp, with no network and no API key. It agrees with the hosted model on **100% of fields**.

![The Last Satellite: a shader-lit Earth, a decaying orbit, and a console that reads what OPS-SAT left behind](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/screens/01-hero.png)

## The problem: a dead satellite can't explain itself

OPS-SAT was ESA's flying laboratory: a CubeSat that teams outside ESA could upload experiments to. Over four and a half years it sent home thousands of telemetry fragments. Then, in the words of its mission-end coverage, it was *"impacted by the recent unexpectedly strong increase in solar activity that began in early 2024"*, and it came down early.

Some of what it sent is now **OPSSAT-AD**:
- 2,123 telemetry segments from three magnetometers and six photodiodes;
- each segment labelled nominal or anomalous by three ESA operations engineers and two ML experts.

The labels say **that** something was wrong. Nothing in the archive says **why**.

That's the trap. Point a modern AI at this archive and ask "what happened to segment 204?" and it will give you a confident, plausible, completely made-up story. A sensor fault. A reboot. Cosmic rays. The data can't contradict it, because the people who could are gone.

**The failure you have to fear isn't "the model is wrong." It's "the model invents a memory the archive doesn't hold, and you believe it."**

## What exists today, and the gap

| Option | What it gives you | What it can't tell you |
|---|---|---|
| Read the paper | A benchmark: FCNN at AUCPR 0.979 | Which of *these* segments to look at first, or what the documents say about them |
| Train your own deep model | Maybe the paper's number, after a training loop | Whether its probabilities mean anything (calibration) |
| Ask a general chatbot | A fluent explanation | Whether a single word of it is in the archive |
| **The Last Satellite** | A calibrated anomaly queue, cited documents, a card per segment | It tells you what it **doesn't** know: *"Root cause not documented in the archive."* |

## What I built

**The Last Satellite** is a *Mission Memory Engine*: an archival investigation console with two open models, one evidence layer and one rule.

- **TabPFN-v2** reads every archived segment and gives a **calibrated probability** that it's anomalous. It ranks all 529 test segments into *prioritise / queue / archive* and shows which **measured** characteristics drove each score.
- **Qwen3-8B + a Tinker LoRA** reads the mission's documents. It extracts **8-field, source-linked records**, rebuilds the timeline (*event* dates kept apart from *publication* dates), explains telemetry terms **with citations**, and writes investigation notes split into **KNOWN** and **NOT KNOWN**.
- **Every statement on screen** is either `[measured]` from the raw signal or `[cited]` from a document, **verbatim**.
- **A root cause is never asserted** unless a source states one, and the archive has no per-segment incident reports. So it says so.
- **The analyst has the last word:** Confirm, Reject or Investigate, stored as feedback.
- **Export:** one click bundles documents, records, cards, feedback and every evaluation file into a portable mission-memory archive.
- **The console** is one cinematic scroll from orbit to re-entry. Behind it, a shader-lit Earth whose city lights burn like candles, and a tiny CubeSat whose orbit decays as you read. At the end the planet warms to marigold and the satellite streaks in.

**Why it fits Ghost in the Machine:** the ghost isn't a monster. It's a voice from a machine that no longer exists: 303,493 readings from a spacecraft that's gone, and a memory that's easy to fake. This project makes the ghost speak only in its own words. Measured, cited, or **unknown**.

## Demo

The video above is the whole tour. The console talks to the live FastAPI backend when it's running. Without it, it falls back to a **labelled archived snapshot of real API responses**, so it works anywhere.

**The signal that should not be there.** Pick one of six candles: six real segments from the official test split, labels hidden. Step through the signal, the 18 measured features, TabPFN's probability, the documents, the most similar past segments, and the investigation card. Then **reveal the truth**.

![True positive: a 16-sample run of exact zeros, P = 1.000, prioritise. The card separates what is measured, what is cited, and what is not known.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/screens/03-reveal-true-positive.png)

**And the one it missed.** The demo set deliberately includes the false alarm and a missed anomaly. Notice the banner on the summary: the fine-tuned interpreter's draft was **rejected by the validator**, so the card fell back to plain, deterministic text. More on that below.

![Missed anomaly: P = 0.098, below the threshold chosen on training data. Shown, not hidden.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/screens/03b-missed-anomaly-reveal.png)

**Ask the archive. It tells you what it doesn't know.**

![Mission Memory: cited answers on the left; "missing from the archive" on the right](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/screens/05-memory-unknown.png)

**The queue.** 529 segments ranked by TabPFN, each with a card and three buttons: Confirm, Reject, Investigate.

![Investigation queue with an open card](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/screens/04-queue-card.png)

## Code

{% github advikdivekar/wake %}

## How I built it

**The rule behind all of it: the models read, code measures, and nothing is claimed that the archive cannot show.**

![The models read. Code measures. Nothing is claimed that the archive cannot show.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/architecture.png)

Language models are brilliant readers and terrible witnesses. TabPFN is a superb estimator, but a probability is not an explanation. So each job goes to whatever can be held accountable for it, and **five independent checks** stand between the models and the screen:

1. **The output parses** into the 8-field schema (Pydantic).
2. **Every quoted sentence exists verbatim** in its source document (substring check).
3. **Channel IDs and dates are cross-checked** by an independent regex reader that never saw the model.
4. **A "root cause" must be stated, unhedged, by a cited source.** "May have been caused by…" maps to `unknown`.
5. **Signal facts come from plain code**, never from a model: zero runs, gaps, peaks, noise.

**The data: real, public, and licence-aware.**
- **Telemetry:** OPSSAT-AD from Zenodo, md5-verified, CC-BY-4.0.
- **Documents:** 20 public sources (the benchmark paper via Europe PMC's open-access API, the dataset code, Wikipedia, ESA pages, news reprints) chunked into 304 passages. Full text is stored only where the licence allows (CC-BY, CC-BY-SA, MIT); everything else gets ≤300-character excerpts and a link.
- **Timeline:** every one of its 11 entries is a verbatim quote, checked against the stored text before it may appear.

---

## Best Use of TabPFN

## 0.979 → 0.989, with no training loop

**The published state of the art on this dataset is a fully connected neural network, trained, tuned and reported in *Scientific Data* in 2025. TabPFN-v2 never ran a training loop on this data. I handed it the training rows and the paper's own 18 features, and it beat the paper on the official test split. Then I engineered better features, and it beat the paper by more.**

That's the point. The anomaly detector at the heart of a mission-memory console shouldn't need a GPU, a hyperparameter sweep and a week. It should need a table.

![Same 18 features as the paper. TabPFN on top.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/like_for_like.png)

| Official test split (529) | AUCPR | F1 | MCC |
|---|---|---|---|
| FCNN, best published (Sci Data 2025) | 0.979 | 0.946 | 0.932 |
| **TabPFN-v2, paper's 18 features** | **0.989** | **0.950** | **0.937** |
| **TabPFN-v2, selected features** | **0.996** [0.989–1.000] | **0.982** [0.963–0.996] | **0.977** |

Brackets are 95% bootstrap CIs over test segments.

My goal wasn't a big number. It was **a big number I could defend line by line.** Here is exactly how.

### 1. Reproduce the paper before you try to beat it

I downloaded OPSSAT-AD, verified both md5 checksums, and counted everything myself:
- 2,123 segments, 303,493 points, 9 channels, 20.4% anomalous;
- 1,594 train and 529 test segments.

*The paper's text says 1,494 training segments; its own Table 1 and the released data both say 1,594.*

Then I ported the published feature code. It reproduces **16 of the 18 features exactly** (99.97% of all values). On the way it caught a nasty bug of mine: the raw file has **22,115 duplicate timestamps**, and a non-stable sort silently changed every derivative feature.

### 2. Re-verify the bar programmatically

I didn't copy the benchmark from a PDF by eye. The script pulls the paper's full text (JATS XML) from Europe PMC and checks every number in Table 3. The bar to beat is **FCNN: AUCPR 0.979, F1 0.946, MCC 0.932** (best unsupervised: MO-GAAL at 0.779). The 2025 correction notice only re-ordered figures; no table changed.

### 3. Choose everything on training data only

I ran 5-fold CV on the **training split**, grouped so neighbouring segments of a channel never straddle folds. Each candidate feature group had to earn its place:

![Which extra features earn their place? Decided on training data only.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/feature_ablation.png)

- **Kept:** zero runs & gaps, autocorrelation and robust spread, which together raised CV AUPRC from **0.9704** to **0.9768**.
- **Dropped:** spectral features and channel identity, which didn't help.
- **Ensemble size:** 8 estimators won (CV 0.9781).

### 4. Let the operator choose the trade-off

Every threshold comes from **training out-of-fold** predictions, before the test split was opened:
- **max-F1** at 0.617;
- **prioritise** at ≥ 0.80, where precision is ≥ 0.95;
- **queue** at ≥ 0.05, where recall is ≥ 0.98.

![The queue is a trade-off you choose, from training data.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/threshold_tradeoff.png)

### 5. Run the test split once

A guard logs every test-set run and **refuses to run the same configuration twice**. One shot:

![529 archived segments. 1 false alarm, 3 missed anomalies.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/errors_529.png)

**415 nominal segments correctly left in the archive, 110 anomalies correctly flagged, 1 false alarm, 3 misses.**

### 6. Checked before trusted

Same split, same features, same folds. Five baselines and a heuristic:

![With engineered features, everyone gets better. TabPFN still leads.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/selected_features.png)

| Official test split | AUCPR | F1 | MCC |
|---|---|---|---|
| **TabPFN-v2** | **0.996** | **0.982** | **0.977** |
| Random Forest | 0.994 | 0.973 | 0.966 |
| XGBoost | 0.993 | 0.968 | 0.960 |
| LightGBM | 0.990 | 0.969 | 0.960 |
| Logistic regression | 0.987 | 0.956 | 0.944 |
| Isolation Forest (unsupervised) | 0.401 | 0.499 | 0.362 |
| "Lots of zeros or a gap" rule | 0.293 | 0.527 | 0.414 |

**A win, but on my features not a thrashing.** Good features lift every model. Against Random Forest, TabPFN is a **statistical tie** (McNemar p = 0.63; AUPRC difference +0.002, 95% CI −0.0005 to +0.006). Against LightGBM and XGBoost, the paired-bootstrap AUPRC differences sit just above zero, and against logistic regression TabPFN wins with p = 0.03.

That's why the like-for-like table at the top matters most. **On the paper's own features, TabPFN beats the tuned trees by ~0.02 AUCPR, and the paper's neural network, out of the box.**

### 7. A probability that means what it says

The probability *is* the investigation queue, so it has to be honest. Brier score on test: **0.0073**.

![When it says 13%, it means 13%.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/calibration.png)

### 8. Things I got wrong first

- **TabPFN refused to run on CPU** with more than 1,000 training rows. Apple's MPS backend was faster anyway, with identical AUPRC.
- **TabPFN and XGBoost segfault when loaded in the same process** on macOS, because two OpenMP runtimes collide (exit 139). Now they run as separate pipeline stages.
- **The newest TabPFN weights want an account and a non-commercial licence.** TabPFN v2 downloads without either (Prior Labs License: Apache-2.0 + attribution), so every number here is v2.
- **My first telemetry plot drew 553 "gaps"** that were really just artefacts of downsampling. Gaps are now computed on raw samples only.

---

## Best Use of Tinker

## 65.3% → 93%, for 83 cents, and it stopped inventing

**Qwen3-8B out of the box makes up channel IDs and paraphrases quotes, and with a confident tone that is exactly how false memories get made. It scored 65.3%. Same model, same prompt, same validator: after 83 cents of Tinker, all-in, it scored 93.0%.**

I didn't need a model that knows everything about spacecraft. I needed one that **copies instead of inventing**, and fine-tuning is how a small model learns that.

![Same model, same prompt, same validator. Only $0.22 of training changed.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/tinker_before_after.png)

| | base Qwen3-8B | **Tinker LoRA** |
|---|---|---|
| **Field-level exact match, validation** | 65.3% | **93.0%** [90.7–94.8] |
| Field-level exact match, held-out test documents | 72.2% | **86.3%** [83.2–88.9] |
| Channel IDs correct | 70.8% | **100%** |
| Evidence copied verbatim from the source | 81.1% | **100%** |
| "Unknown" used correctly | 82.1% | **99.8%** |
| Whole record exactly right | 0% | **44.4%** |
| Investigation notes passing every check (task D) | 56% | **100%** |
| Errors caught by the independent validator | 40 | **0** |
| Unsupported root causes | 0 | **0** |

My goal wasn't the biggest number. It was **a real number at the lowest price I could defend.** Here is exactly how.

![The fine-tuning pipeline](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/finetune_pipeline.png)

### 1. Freeze the metric before anything trains

Before any model saw any data, I froze the headline: **field-level exact match on held-out documents, scored on raw output before any repair.** Companion metrics:
- valid-schema rate;
- verbatim-evidence rate;
- unsupported-root-cause count;
- correct use of "unknown";
- Wilson CIs;
- a paired McNemar test against the base model.

### 2. Shrink the bill before you shrink the model

Tinker bills per token, so the output is 8 compact lines that code turns into Pydantic JSON:

```plaintext
channel_id: CADC0873
sensor_type: magnetometer
units: ?
event_date: 2024-05-22
observation: On 22 May 2024 the magnetometer I_B_FB_MM_1 reported a run of zero values.
operational_response: ?
root_cause: ?
evidence: On 22 May 2024 the magnetometer I_B_FB_MM_1 reported a run of zero values.
```

A full training example, prompt and passage included, is **about 380 tokens**.

### 3. Price the options, then pick

Training per million tokens:
- **Qwen3-8B: $0.44.**
- Qwen3.5-4B: $0.737. A smaller model is not automatically a cheaper one.
- GPT-OSS-20B: $0.396, but it's a reasoning model whose thinking tokens would cost more at sampling time and break the format.

### 4. Train: rank-16 LoRA, loss on the answer only, 5 minutes

```python
renderer = renderers.get_renderer("qwen3_disable_thinking", tok)
mi, w = renderer.build_supervised_example(messages, train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE)

fb = tc.forward_backward(batch, loss_fn="cross_entropy")
op = tc.optim_step(tinker.AdamParams(learning_rate=lr_t, beta1=0.9, beta2=0.95, eps=1e-8))
```

- **Data:** examples across four tasks (extraction, timelines, terminology with citations, investigation notes).
- **Schedule:** batch 16, linear LR decay, 3 epochs, a checkpoint every epoch. The final run took **5.1 minutes**.
- **Split by document family, never by chunk:** the test documents (the benchmark paper plus Wikipedia) never appear in training, and the paper's arXiv preprint is **excluded everywhere** as a near-duplicate.
- **Budget guard:** it prices every job from local token counts *before* submitting and refuses anything over the cap. I started with **$0.93**.

### 5. Find the knee of the curve

![Two and a half cents buys +25 points.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/learning_curve.png)

| Run | Est. cost | Validation field exact match |
|---|---|---|
| base Qwen3-8B, untrained | n/a | 65.3% |
| smallest run | $0.025 | 90.8% |
| run 2 | $0.049 | 91.8% |
| run 3 | $0.097 | 92.2% |
| **final model** | **$0.224** | **93.0%** |

**Two and a half cents of training buys +25 points.** Everything after that is the last few points, bought cheaply.

### 6. Validation error analysis found *my* bugs

Midway through, most remaining "errors" were the model **correctly refusing** to quote code blocks, footnotes and markdown bullet lists that my labelling rules had picked as "observations".
- I tightened the spec to prose-only sentences.
- I **killed a half-finished run** rather than pay to finish it on bad labels.
- I retrained once.
- The test set stayed sealed the whole time.

### 7. Is the gain real or noise?

Paired, cell by cell, on the same 576 field cells: **95 cells only the fine-tune got right, 14 only the base got right**. Exact McNemar **p = 5.8×10⁻¹⁶**.

![It stopped inventing channel IDs and started quoting sources.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/task_a_fields.png)

The base model's **40 validator catches** are what the validator is for: channel IDs and quotes that don't exist in the source. **The fine-tune made zero.** Even after the validator repairs the base model's output, it reaches 78.5%, still below the fine-tune's *unrepaired* 86.3%.

### 8. Rent the training. Keep the weights.

I exported the adapter as PEFT (one tensor rename: `unembed_tokens` → `lm_head`), converted it to GGUF with llama.cpp, and ran it over a Q4_K_M Qwen3-8B base:

> **92.5% field exact match on held-out passages, 100% field-for-field agreement with the same checkpoint on Tinker, 4.7 s per passage.** M3 Pro, 18 GB, Hugging Face offline, no Tinker key in the environment.

### The whole bill

![Where the $0.83 went. Everything on Tinker.](https://raw.githubusercontent.com/advikdivekar/wake/main/docs/charts/cost_breakdown.png)

| Item | Est. cost |
|---|---|
| Learning-curve runs (50 / 100 / 200) | $0.17 |
| A run I stopped at 65/84 steps after finding label bugs | $0.17 |
| **Final model (3 epochs)** | **$0.22** |
| Downloadable sibling adapter (see Known edges) | $0.10 |
| All evaluation on Tinker | $0.17 |
| **Everything on Tinker** | **$0.83** |

*Token counts at Tinker's list prices, logged before every job. Base-model validation ran locally for free.*

---

## Known edges (measured, not hidden)

I'd rather you hear these from me, with numbers.

- **I missed my own target.** I set **95%** before training. The model got **93.0% on validation and 86.3% on test**. Most of the gap is one judgement call: *which* sentence is "the observation" in an unfamiliar document.
- **Fine-tuning made one task worse.** Citing the right source for a telemetry term fell from **96.2% to 82.7%** (p = 0.016). That task had only 32 training examples, and the tuned model learned to answer "not in the archive" too eagerly.
- **The offline adapter is a sibling.** Tinker doesn't let you download *sampler* checkpoints, which is all my final run had saved. So the offline adapter is a smaller sibling configuration, retrained with a downloadable checkpoint (validation 92.3% vs 93.0%). The training script now saves both kinds.
- **The labels are a spec, not human annotation.** "Exact match" means agreement with a deterministic spec on unseen documents. Some fields (units, operational responses) appear in only a handful of held-out passages.
- **The validator rejects my own model.** In the demo, **4 of 6** investigation cards fell back to deterministic text. In one, the interpreter wrote that the root cause "*is documented*", which contradicts its own NOT KNOWN list. The guard caught it. I'd rather show a plain card than a confident wrong one.
- **TabPFN's edge over Random Forest on my engineered features is a statistical tie.** Its clear win is like-for-like, on the paper's features.

**What went wrong on the way (and made it better):** my base-model comparison was unfair at first. The prompt never named the eight fields and the parser rejected markdown, so I fixed both *before* training anything. A root-cause rule briefly treated "*due to* the underlying nature of the mission" as a cause, and a Q&A ranking tweak made one answer prettier but quietly removed the "cause unknown" warning from others. Both were caught and reverted.

## Why does open innovation matter?

A closed API gives you an answer. Open weights and open data give you **a way to check it.**

- **I could audit the archive.** The dataset authors published the data *and* the feature code, so I reproduced their features to the decimal and found a typo in their split count. A ghost story you can fact-check is a different kind of story.
- **I could change the model, not just the prompt.** Base Qwen3-8B invented channel IDs. Twenty-two cents of LoRA training stopped it.
- **I could test the probability.** With TabPFN's weights and the public test split, I measured calibration myself (Brier 0.0073) instead of trusting a number someone printed.
- **No meter running, nobody to deprecate it.** The adapter and TabPFN run on the laptop that holds the archive. After a spacecraft dies, its memory shouldn't depend on someone else's API staying up.
- **Memory should be a commons.** OPS-SAT existed because ESA opened a satellite to outsiders. Its memory should stay just as open.

The honest caveat: training ran on Tinker's servers, on public documents only. At run time, nothing leaves the laptop.

## My agent session

I built The Last Satellite with **Claude Code** as a pair, from a written 12-hour plan with a cost estimate up front, a budget guard on every Tinker job and a guard on every test-set run.

- **It read the sources before writing code.** It read Tinker's and TabPFN's docs, re-verified the paper's benchmark table from the full text, and read the original feature code before porting it.
- **It caught its own mistakes:**
  - a duplicate-timestamp sort bug;
  - an unfair base-model prompt;
  - label bugs, found through validation error analysis;
  - a root-cause rule that was too generous.
- **It stopped spending when the data said to.** It killed a half-finished run on bad labels, and when the final checkpoint turned out to be undownloadable, it asked me before spending the last of my credit.
- **It reverted its own "improvement"** when it made the honesty guarantees worse.
- **It kept a running cost ledger** from the first job.

## Prize categories

**Best Use of TabPFN.** TabPFN is the engine of the console, not a bolt-on: every probability, every queue position and every "top measured characteristic" comes from it.
- **Official OPSSAT-AD test split, one logged run:** **AUCPR 0.996, F1 0.982, MCC 0.977**, against the best published **0.979 / 0.946 / 0.932**.
- **On the paper's own 18 features, with no training loop:** **0.989 / 0.950 / 0.937**, beating the paper and the tuned tree ensembles.
- **Rigour:** calibrated (Brier 0.0073), with thresholds chosen on training data only, and compared against five baselines with bootstrap CIs and McNemar tests, including the tie I report against myself.

**Best Use of Tinker.** The LoRA fine-tune (loss on answers only, per-epoch checkpoints), the learning curve, a budget guard, held-out evaluation with paired statistics, and the adapter download behind the offline story all ran on Tinker. **$0.22 for the final model, $0.83 for everything.**
- **Same base model, same prompt, same validator:** extraction **65.3% → 93.0%** on validation (**72.2% → 86.3%** on held-out test documents), verbatim evidence **81% → 100%**, investigation notes **56% → 100%**, and **0 invented root causes**.

*Built solo, with Claude Code, over one long Halloween night.*

**Two open models. Eighty-three cents. One rule: measure it, cite it, or call it unknown.** If that sounds like the right way to remember a satellite, a ❤️ or 🦄 helps more people find it.

If a machine you depend on went silent tomorrow, what's the one thing you'd want its archive to remember? Leave it in the comments.
