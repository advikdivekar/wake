"""Scoring for tasks A-D (frozen in evaluations/tinker_metric_spec.json)."""
from __future__ import annotations

import math
import re

from scipy.stats import binomtest

from training.tinker import spec


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def mcnemar(a: list[bool], b: list[bool]) -> dict:
    a_only = sum(1 for x, y in zip(a, b) if x and not y)
    b_only = sum(1 for x, y in zip(a, b) if y and not x)
    p = binomtest(a_only, a_only + b_only, 0.5).pvalue if a_only + b_only else 1.0
    return {"base_only_correct": a_only, "tuned_only_correct": b_only, "exact_p": float(p)}


def score_A(examples: list[dict], outputs: list[str]) -> dict:
    cells, per_field = [], {f: {"tp": 0, "fp": 0, "fn": 0, "correct": 0, "n": 0} for f in spec.FIELDS}
    valid = 0; verbatim_ok = verbatim_n = 0; unsupported_rc = 0; null_ok = null_n = 0
    record_exact = 0; validator_flags = 0; validator_caught = 0; post_val_cells = []
    for ex, out in zip(examples, outputs):
        gold = ex["gold"]
        rec, errs = spec.parse_lines(out)
        if rec is not None and not errs:
            try:
                spec.to_record_json(rec); valid += 1
            except Exception:
                pass
        rec = rec or {f: ([] if f in spec.LIST_FIELDS else None) for f in spec.FIELDS}
        val = spec.validate(rec, ex["passage"])
        validator_flags += len(val["flags"])
        all_ok = True
        for f in spec.FIELDS:
            ok = spec.field_equal(f, rec.get(f), gold.get(f))
            ok_after = spec.field_equal(f, val["record"].get(f), gold.get(f))
            cells.append(ok); post_val_cells.append(ok_after)
            if not ok and any(fl.startswith(f) for fl in val["flags"]):
                validator_caught += 1
            all_ok &= ok
            pf = per_field[f]; pf["n"] += 1; pf["correct"] += ok
            pred_pos, gold_pos = bool(rec.get(f)), bool(gold.get(f))
            if pred_pos and gold_pos and ok:
                pf["tp"] += 1
            else:
                pf["fp"] += pred_pos and not ok
                pf["fn"] += gold_pos and not ok
            if not gold_pos:
                null_n += 1; null_ok += not pred_pos
            if f in spec.SPAN_FIELDS and rec.get(f):
                verbatim_n += 1; verbatim_ok += spec.norm_ws(rec[f]) in spec.norm_ws(ex["passage"])
        if rec.get("root_cause") and (not gold.get("root_cause") or
                                      spec.norm_ws(rec["root_cause"]) not in spec.norm_ws(ex["passage"])):
            unsupported_rc += 1
        record_exact += all_ok
    n = len(cells)
    for f, pf in per_field.items():
        p = pf["tp"] / max(pf["tp"] + pf["fp"], 1); r = pf["tp"] / max(pf["tp"] + pf["fn"], 1)
        pf.update({"exact_match": round(pf["correct"] / max(pf["n"], 1), 4), "precision": round(p, 4),
                   "recall": round(r, 4), "f1": round(2 * p * r / max(p + r, 1e-9), 4)})
    return {"n_passages": len(examples), "n_cells": n,
            "field_exact_match": round(sum(cells) / max(n, 1), 4), "wilson95": wilson(sum(cells), n),
            "field_exact_match_after_validator": round(sum(post_val_cells) / max(n, 1), 4),
            "record_exact_match": round(record_exact / max(len(examples), 1), 4),
            "valid_schema_rate": round(valid / max(len(examples), 1), 4),
            "evidence_fidelity": round(verbatim_ok / verbatim_n, 4) if verbatim_n else None,
            "unsupported_root_causes": unsupported_rc,
            "null_correctness": round(null_ok / max(null_n, 1), 4),
            "validator_flags": validator_flags, "validator_caught_errors": validator_caught,
            "per_field": per_field, "_cells": cells}


def score_B(examples, outputs) -> dict:
    date_ok = pub_ok = verb_ok = verb_n = 0
    cells = []
    for ex, out in zip(examples, outputs):
        gold_dates = [l.split()[1] for l in ex["messages"][-1]["content"].splitlines() if l.startswith("EVENT ") and l != "EVENT ?"]
        pred_lines = [l.strip() for l in out.splitlines()]
        pred_dates = [l.split()[1] for l in pred_lines if l.startswith("EVENT ") and len(l.split()) > 1 and l.split()[1] != "?"]
        ok_d = sorted(set(pred_dates)) == sorted(set(gold_dates))
        gold_pub = ex["publication_date"] or "?"
        pub = next((l.split()[1] for l in pred_lines if l.startswith("PUBLISHED") and len(l.split()) > 1), None)
        ok_p = pub == gold_pub
        # record-vs-publication confusion: publication date wrongly listed as an event date
        for l in pred_lines:
            if "|" in l and l.startswith("EVENT"):
                verb_n += 1; verb_ok += spec.norm_ws(l.split("|", 1)[1]) in spec.norm_ws(ex["passage"])
        date_ok += ok_d; pub_ok += ok_p; cells.append(ok_d and ok_p)
    n = len(examples)
    return {"n": n, "event_dates_exact": round(date_ok / max(n, 1), 4), "publication_date_correct": round(pub_ok / max(n, 1), 4),
            "both_correct": round(sum(cells) / max(n, 1), 4), "wilson95": wilson(sum(cells), n),
            "verbatim_event_sentences": round(verb_ok / verb_n, 4) if verb_n else None, "_cells": cells}


def score_C(examples, outputs) -> dict:
    cite_ok = absent_ok = absent_n = present_n = verb_ok = verb_n = 0
    cells = []
    for ex, out in zip(examples, outputs):
        m = re.search(r"SOURCE:\s*\[?(\d+|none)\]?", out)
        src = m.group(1) if m else None
        d = re.search(r"DEFINITION:\s*(.+)", out)
        defi = d.group(1).strip() if d else None
        if ex["variant"] == "absent":
            absent_n += 1
            ok = src == "none" and (defi in ("?", None))
            absent_ok += ok
        else:
            present_n += 1
            ok = src is not None and src != "none" and int(src) == ex["gold_source"]
            cite_ok += ok
            if defi and defi != "?":
                verb_n += 1
                verb_ok += bool(ex["gold_sentence"]) and spec.norm_ws(defi) == spec.norm_ws(ex["gold_sentence"])
        cells.append(ok)
    n = len(examples)
    return {"n": n, "citation_correct_when_present": round(cite_ok / max(present_n, 1), 4),
            "not_in_archive_correct_when_absent": round(absent_ok / max(absent_n, 1), 4),
            "definition_exact_verbatim": round(verb_ok / verb_n, 4) if verb_n else None,
            "overall": round(sum(cells) / max(n, 1), 4), "wilson95": wilson(sum(cells), n), "_cells": cells}


CAUSE_CLAIM = re.compile(r"\b(caused by|due to|because|root cause (is|was)|resulted from|triggered by)\b", re.I)


def score_D(examples, outputs) -> dict:
    sec_ok = num_ok = cite_ok = no_cause = 0
    cells = []
    for ex, out in zip(examples, outputs):
        has = all(re.search(rf"^{s}\s*$", out, re.M) for s in ("KNOWN", "UNKNOWN", "ACTION"))
        ev = ex["evidence"]
        nums_needed = [f"{ex['probability']:.2f}", str(ev["n_peaks"])]
        if ev["max_zero_run"] > 1:
            nums_needed.append(str(ev["max_zero_run"]))
        if ev["gap_count"] > 0:
            nums_needed.append(str(ev["gap_count"]))
        nums = all(n in out for n in nums_needed)
        cited = [int(x) for x in re.findall(r"\[(\d+)\]", out)]
        cites = all(1 <= c <= len(ex["cites"]) and ex["cites"][c - 1]["relevant"] for c in cited)
        known = out.split("UNKNOWN")[0] if "UNKNOWN" in out else out
        nc = not CAUSE_CLAIM.search(known)
        sec_ok += has; num_ok += nums; cite_ok += cites; no_cause += nc
        cells.append(has and nums and cites and nc)
    n = len(examples)
    return {"n": n, "sections_present": round(sec_ok / max(n, 1), 4), "numbers_correct": round(num_ok / max(n, 1), 4),
            "citations_valid": round(cite_ok / max(n, 1), 4), "no_unsupported_cause": round(no_cause / max(n, 1), 4),
            "all_checks": round(sum(cells) / max(n, 1), 4), "wilson95": wilson(sum(cells), n), "_cells": cells}


SCORERS = {"A": score_A, "B": score_B, "C": score_C, "D": score_D}
