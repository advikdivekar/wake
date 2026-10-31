# The Last Satellite: Mission Memory Engine. Backend Architecture and Frontend Contract

> *"Its mission ended. Its memories did not."*
>
> This file is the **contract between the backend and the frontend console**. The frontend agent builds against the schemas and endpoints below. Until the live API is up, set `USE_FIXTURES=1`, which makes the frontend read the JSON files in `frontend/fixtures/`. Every fixture carries `"illustrative": true`, and the UI must show an **illustrative** badge whenever it renders fixture data.
>
> Repo root: `/Users/advikdivekar/Desktop/wake ` (the folder name ends with a space, so quote paths). Python 3.11 lives in `.venv/`.

---

## 1. What the system is

This is an **archival** analysis system for **OPS-SAT**, an ESA CubeSat that launched in December 2019 and re-entered on **22 May 2024**. It is not live. All telemetry comes from the public **OPSSAT-AD** dataset (Zenodo 10.5281/zenodo.12588359, CC-BY-4.0, verified md5).

The dataset has 2,123 labelled segments across 9 channels: 3 magnetometer and 6 photodiode. The official split is 1,494 train and 529 test segments, about 20% anomalous.

| Channel | Name | Kind |
|---|---|---|
| CADC0872 | I_B_FB_MM_0 | magnetometer |
| CADC0873 | I_B_FB_MM_1 | magnetometer |
| CADC0874 | I_B_FB_MM_2 | magnetometer |
| CADC0884 | I_PD1_THETA | photodiode |
| CADC0886 | I_PD2_THETA | photodiode |
| CADC0888 | I_PD3_THETA | photodiode |
| CADC0890 | I_PD4_THETA | photodiode |
| CADC0892 | I_PD5_THETA | photodiode |
| CADC0894 | I_PD6_THETA | photodiode |

```
OPSSAT-AD (Zenodo, CC-BY-4.0) ─► app/ingestion ─► SQLite data/processed/mission.db
                                       │            (segments, telemetry_points, features)
              app/telemetry/features.py ─► TabPFN "Telemetry Analyser" ─► predictions
Public OPS-SAT documents ─► chunker ─► FTS5 + vectors ─► hybrid retrieval (citations)
                                       │
   "Mission Memory Interpreter" = Qwen3-8B + LoRA adapter trained on Tinker (hosted),
    served LOCALLY by llama.cpp (llama-server :8081), no Tinker calls at runtime
                                       ▼
          Evidence Integration Layer ─► Investigation Card ─► Human Review (feedback)

FastAPI  http://localhost:8000   ◄──  Streamlit console  http://localhost:8501
```

### Run commands
| Command | What it does |
|---|---|
| `make api` | `uvicorn app.api.main:app --port 8000` |
| `make ui` | `streamlit run frontend/Home.py --server.port 8501` |
| `make app` | runs llama-server :8081, the API and the UI together |
| `make ui-fixtures` | runs the UI with `USE_FIXTURES=1` (no backend needed) |

### Frontend environment variables
- `API_BASE`: default `http://localhost:8000`.
- `USE_FIXTURES`: `1` reads `frontend/fixtures/<fixture_name>.json`. The fixture name for each endpoint is listed in §4.
- **Fixture format:** an object fixture is the endpoint's JSON plus `"illustrative": true`. A list fixture is wrapped as `{"illustrative": true, "data": [...]}`, so the loader should unwrap `data`.
- Fixtures for `health`, `mission`, `channels`, `segments`, `segment_1`, `features_1`, `telemetry_CADC0872`, `config` and `evaluations` are captured from the **real** API. All others contain `EXAMPLE` placeholder values. Regenerate them with `make fixtures`.
- **Shared Python helpers:** the frontend may import `app.api.schemas` for typing, but must talk to the backend over HTTP only.

---

## 2. Rules the UI must respect (judging depends on these)

1. **No hard-coded metrics.** The Model Laboratory renders only what the `/evaluations*` endpoints return. A missing file shows *"not yet measured"*.
2. **Illustrative means labelled.** Any fixture or example data shows a visible `illustrative` badge.
3. **Ground truth stays hidden** until the user clicks *Reveal*, which calls `POST /investigations/{card_id}/reveal` or `GET /segments/{id}?reveal=true`.
4. **The tone is archival, never live.** Don't use wording like "live feed" or "incoming". Use "archived transmission" or "recorded on" instead.
5. **Root causes appear only with a citation.** If a card's `root_cause` is null, show **"Unknown: not documented in the archive."** Always render the *What is NOT known* list.
6. **Similar segments are a resemblance, not a shared fault.** Show the `note` field verbatim.
7. **Event dates differ from publication dates.** The timeline shows both, distinguished by `date_kind`.
8. **Footer on every page** (verbatim):
   *"Archival analysis of the public OPSSAT-AD dataset (CC-BY-4.0; code MIT). TabPFN weights: see licence notes in the Model Laboratory. Interpreter adapter trained on Tinker (hosted service); inference runs locally."*

### Suggested design tokens
These follow a restrained ofrenda/memorial look: a scientific instrument, not horror. The frontend agent may refine them.
```css
--marigold:#E8A33D; --candle:#F6E7C1; --ember:#B5522B; --night:#12100E;
--ash:#2A2622; --bone:#EDE6DA; --signal:#7FB7BE; --alert:#D9534F; --muted:#8C847A;
```
- Use a serif for display text (e.g. *Cormorant Garamond* or *EB Garamond*) and monospace for data (*JetBrains Mono* or *IBM Plex Mono*).
- In plots, draw telemetry lines in `--signal`. Shade zero runs in `--ember` at 25% opacity, mark gaps with dashed `--muted` vertical bands, and draw the selected segment with a `--marigold` outline.

---

## 3. Schemas (Pydantic in `app/api/schemas.py`; JSON shapes are stable)

All timestamps are ISO-8601 UTC strings. Nullable fields are always present and set to `null`, never omitted.

```jsonc
// Citation: every factual statement from documents carries one
{ "doc_id":"opssat-ad-paper", "chunk_id":"opssat-ad-paper#c012", "title":"The OPS-SAT benchmark ...",
  "url":"https://doi.org/10.1038/s41597-025-05035-3", "location":"§Methods, p.4",
  "excerpt":"verbatim text from the source", "score":0.71, "license":"CC-BY-4.0" }

// Segment
{ "segment_id":1, "channel":"CADC0872", "channel_name":"I_B_FB_MM_0", "channel_kind":"magnetometer",
  "split":"train", "sampling":1, "n_points":280,
  "start":"2022-06-01T23:42:54Z", "end":"2022-06-02T00:01:33Z",
  "label":null }                       // 0|1 only when reveal=true

// TelemetrySeries
{ "segment_id":1, "t":["2022-06-01T23:42:54Z", "..."], "v":[-2.1487e-05, "..."],
  "gaps":[{"start":"...","end":"...","seconds":31.0}],
  "zero_runs":[{"start_idx":40,"end_idx":71}], "peaks_idx":[12, 88] }

// Prediction
{ "segment_id":1, "probability":0.87, "decision":"prioritise",      // prioritise | queue | archive
  "thresholds":{"high":0.60,"low":0.30}, "model":"tabpfn-v2:n8:extra",
  "contributors":[{"feature":"gaps_squared","value":309,"z":3.1,"importance":0.08,
                   "plain":"Unusually large gaps between samples"}] }

// SimilarSegment
{ "segment_id":77, "distance":0.42, "label":1, "channel":"CADC0872",
  "note":"Resemblance in measured characteristics, not evidence of a shared fault." }

// MemoryRecord (Interpreter task A output)
{ "record_id":"rec-0001", "channel_id":"CADC0872", "sensor_type":"magnetometer", "units":null,
  "event_date":null, "publication_date":"2025-04-29", "observation":"...",
  "operational_response":null, "root_cause":null,
  "evidence_excerpt":"verbatim substring of the source", "unknown_fields":["root_cause","units"],
  "source": Citation }

// InvestigationCard
{ "card_id":"inv-1-1", "segment_id":1, "created_at":"...",
  "prediction": Prediction,
  "signal_evidence":{"zero_runs":1,"max_zero_run":31,"gap_count":2,"max_gap_s":31.0,
                     "n_peaks":4,"irregular_sampling":false,"noise_std":1.2e-06},
  "historical_context":[SimilarSegment],
  "documents":[Citation],
  "known":[{"statement":"Segment contains a 31-sample run of exact zeros","basis":"measured","citations":[]},
           {"statement":"Zero-value fragments are an annotated anomaly type in OPSSAT-AD","basis":"cited","citations":[Citation]}],
  "unknown":["Root cause of this signal behaviour is not documented in the archive"],
  "suggested_action":"Prioritise for analyst review",
  "summary":"Validated natural-language summary ...", "summary_model":"qwen3-8b+lora (llama.cpp, local)",
  "review_status":"unreviewed",        // unreviewed | confirmed | rejected | investigating
  "ground_truth":null }                // 0|1 only after reveal

// Feedback
{ "card_id":"inv-1-1", "action":"confirm", "note":"optional text", "at":"..." }  // confirm | reject | investigate

// AskAnswer (Mission Memory Q&A)
{ "question":"...", "answer":"...", "citations":[Citation],
  "missing":["The archive contains no incident report explaining ..."], "model":"..." }

// EvalIndexItem
{ "name":"tabpfn_test_results.json", "kind":"json", "produced_by":"make tabpfn-test",
  "created_at":"...", "git_sha":"abc1234" }
```

---

## 4. REST endpoints (FastAPI, JSON, localhost, no auth)

| Method & path | Returns | Fixture name |
|---|---|---|
| `GET /health` | `{status, models:{tabular,lm}, illustrative?}` | `health` |
| `GET /mission` | `{name, operator, launch_date, reentry_date, status:"archival", datasets:[{name,doi,license,segments,train,test,anomaly_rate}], channels:[...], timeline:[{date,date_kind:"event"\|"publication",title,citation}]}` | `mission` |
| `GET /channels` | `[{channel,channel_name,kind,n_segments,anomaly_rate_train}]` | `channels` |
| `GET /channels/{ch}/telemetry?start=&end=&max_points=5000` | `TelemetrySeries` (`segment_id`=null) + `segments:[{segment_id,start,end,split}]` | `telemetry_CADC0872` |
| `GET /segments?split=test&sort=probability&limit=100&status=` | `[{...Segment, probability, decision, review_status}]` | `segments` |
| `GET /segments/{id}?reveal=false` | `{segment:Segment, series:TelemetrySeries}` | `segment_1` |
| `GET /segments/{id}/features` | `{features:{name:value}, published_18:[names], extras:[names]}` | `features_1` |
| `POST /predict` body `{segment_id}` or `{channel,sampling,t:[...],v:[...]}` | `Prediction` | `prediction_1` |
| `GET /segments/{id}/similar?k=5` | `[SimilarSegment]` | `similar_1` |
| `POST /investigations` body `{segment_id, use_lm:true}` | `InvestigationCard` | `card_1` |
| `GET /investigations?status=` | `[InvestigationCard]` | `cards` |
| `GET /investigations/{card_id}` | `InvestigationCard` | `card_1` |
| `POST /investigations/{card_id}/feedback` body `{action,note}` | updated `InvestigationCard` | n/a |
| `POST /investigations/{card_id}/reveal` | card with `ground_truth` set | `card_1_revealed` |
| `POST /memory/ask` body `{question, k:6}` | `AskAnswer` | `ask` |
| `POST /memory/extract` body `{text}` | `MemoryRecord` | `extract` |
| `GET /memory/timeline` | `[{event_date,publication_date,event,citation}]` | `timeline` |
| `GET /documents` | `[{doc_id,title,url,license,stored_mode:"full"\|"excerpt",n_chunks,retrieved_at,category}]` | `documents` |
| `GET /documents/{doc_id}` | `{document, chunks:[{chunk_id,location,text}]}` | `document_opssat-ad-paper` |
| `GET /evaluations` | `[EvalIndexItem]` | `evaluations` |
| `GET /evaluations/{name}` | JSON → parsed JSON; CSV → `{columns, rows}`; MD → `{markdown}`; PNG → image bytes | `eval_<name>` |
| `GET /demo` | `[{segment_id, blurb}]` (case hidden) | `demo` |
| `GET /demo/{segment_id}/steps` | `{segment, series, features, prediction, citations, similar, card}` (no label) | `demo_steps_1` |
| `GET /demo/{segment_id}/reveal` | `{segment_id, label, case:"TP"\|"TN"\|"FP"\|"FN", predicted, probability}` | `demo_reveal_1` |
| `GET /export` | `application/zip` (mission memory archive) | n/a |
| `GET /config` | `{language_model:{...}, tabular_classifier:{...}, thresholds:{...}, retrieval:{...}}` | `config` |

Errors use `{"detail": "..."}` with the usual HTTP status codes.

---

## 5. Evaluation files (fixed names in `evaluations/`, read by the Model Laboratory)

Every JSON file includes `produced_by`, `git_sha` and `created_at`. **The Lab must tolerate missing files.**

| File | Content |
|---|---|
| `dataset_verification.json` | checksums, row/segment counts, per-channel counts, split, anomaly rate |
| `feature_reproduction.json` | per-feature agreement between our extractor and `dataset.csv` |
| `published_benchmark.md` | published OPSSAT-AD results with citations (the bar) |
| `ours_vs_published.md` | side-by-side table |
| `tabpfn_cv_results.csv` / `baselines_cv_results.csv` | `variant, fold, auprc, auroc, f1, precision, recall, mcc` |
| `tabpfn_test_results.json` / `baselines_test_results.json` | `{models:[{model, precision, recall, f1, auprc, auroc, mcc, ci:{metric:[lo,hi]}, confusion:[[tn,fp],[fn,tp]], threshold}]}` |
| `significance_tests.json` | McNemar / bootstrap differences, TabPFN vs each baseline |
| `pr_curve.json` | `{model:[{threshold,precision,recall}]}` |
| `threshold_tradeoff.csv` | `threshold, missed_anomalies, false_alerts, precision, recall` |
| `calibration.json` | `{bins:[{p_mean,frac_pos,count}], brier}` |
| `feature_importance.json` | `[{feature, importance, std}]` |
| `tinker_metric_spec.json` | frozen metric definition (written before training) |
| `tinker_model_choice.md` | model/price comparison |
| `tinker_learning_curve.json` | `[{n_examples, val_exact_match, cost_usd, tokens}]` |
| `tinker_eval_A.json` … `tinker_eval_D.json` | `{base:{...}, tuned:{...}, paired:{mcnemar_p, wilson:{...}}, per_field:{...}}` |
| `offline_inference.json` | local llama.cpp run of base + adapter on held-out passages |
| `tinker_cost.json` | tokens and USD per job |
| `test_run_log.jsonl` | one line per official test-set run |

---

## 6. Console sections and their endpoints

1. **Mission Archive**: `/mission`, `/documents`, `/memory/timeline`. Shows mission identity, datasets, source documents with licences, the channel table, and a *"last transmission"* timeline ending on 22 May 2024.
2. **Signal Observatory**: `/channels`, `/channels/{ch}/telemetry`, `/segments/{id}`. Shows the raw signal per channel with gaps, zero runs and the selected segment highlighted.
3. **Investigation Queue**: `/segments?split=test&sort=probability`, `/investigations*`, `/segments/{id}/similar`. Segments are ranked by probability with decision chips. The page also shows the card view and the Confirm / Reject / Investigate buttons, which call `POST …/feedback`.
4. **Mission Memory**: `/memory/ask`, `/memory/extract`. Answers come with citation cards and a *"Missing from the archive"* panel built from `missing[]`.
5. **Model Laboratory**: `/evaluations*` only. Covers TabPFN vs baselines, ours vs published, confusion matrices, PR curves, the threshold trade-off, calibration, feature importance, Tinker base vs tuned, the learning curve with cost, offline inference proof, limitations and licence notes.

**Guided demo, "The signal that should not be there"** (one click):
1. `GET /demo` picks a segment.
2. `GET /demo/{id}/steps` loads the payload.
3. The user steps through: raw signal → features → TabPFN probability → documentary memory → similar past segments → investigation card.
4. `GET /demo/{id}/reveal` shows the ground truth and the TP/TN/FP/FN case.

The demo set deliberately includes a false positive and a missed anomaly, and the UI should present them honestly.

---

## 7. Replaceability (`config.yaml`)
```yaml
language_model:
  backend: llamacpp            # llamacpp | tinker | template
  base_model: Qwen/Qwen3-8B
  gguf: models/Qwen3-8B-Q4_K_M.gguf
  adapter: models/adapter.gguf
  server: http://localhost:8081
tabular_classifier:
  backend: tabpfn              # tabpfn | xgboost | rf | lr
  path: models/tabpfn_final.pkl
thresholds: {high: null, low: null}   # filled by training/tabpfn/threshold.py
retrieval: {embedding_model: BAAI/bge-small-en-v1.5, fusion: rrf, k: 6}
```
The interfaces are `app/prediction/base.py::TabularClassifier` (`fit`, `predict_proba`, `explain`) and `app/investigation/lm.py::LanguageModel` (`generate(prompt, max_tokens) -> str`).
