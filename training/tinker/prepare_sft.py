"""Build the Tinker SFT dataset (tasks A-D) from the document archive.

Split is BY DOCUMENT FAMILY (near-duplicates such as the paper and its arXiv preprint share a family),
so no held-out passage or near-duplicate is ever seen in training.
Outputs data/processed/sft/{train,val,test}.jsonl and evaluations/sft_dataset_stats.json.
"""
from __future__ import annotations

import json
import random
import re

from app.common.channels import CHANNELS
from app.common.paths import DATA_PROCESSED, write_eval_json
from app.ingestion.documents import chunk
from app.memory.db import connect
from training.tinker import spec

OUT = DATA_PROCESSED / "sft"
OUT.mkdir(parents=True, exist_ok=True)
RNG = random.Random(2137)

FAMILY = {
    "opssat-ad-paper": "opssat-ad-paper", "opssat-ad-arxiv": "opssat-ad-paper", "opssat-ad-correction": "opssat-ad-paper",
    "opssat-ad-readme": "opssat-ad-code", "opssat-ad-generator": "opssat-ad-code", "opssat-ad-zenodo": "opssat-ad-code",
}
SPLIT = {  # family -> split. Decided before any model was run; see PROGRESS.md for the rationale.
    # TEST: the OPSSAT-AD paper (only real source of channel mentions) + Wikipedia (dates) + correction
    "opssat-ad-paper": "test", "wikipedia-opssat": "test",
    # VAL (iteration only)
    "opssat-ad-code": "val", "esa-eol-abstract-2024": "val", "esa-reentry-workshop-2025": "val",
    "smallsatnews-mission-completed": "val",
    # TRAIN
    "arxiv-refined-astrometry": "train", "esa-rocketscience-final-hours": "train",
    "solardaily-mission-concludes": "train", "esoc-opssat": "train", "usu-smallsat-2022-ml": "train",
    "tugraz-opssat-mission": "train", "esa-reentry-radio-campaign": "train", "opssat-esa-missions": "train",
}
EXCLUDE = {"opssat-ad-arxiv"}   # near-duplicate preprint of a TEST document: excluded everywhere (no leakage)
MAX_CHARS = 1300


def clean(t: str) -> str:
    t = re.sub(r"<sup>.*?</sup>|\\\[edit\\\]|\[edit\]", "", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def passages_by_doc() -> dict[str, list[dict]]:
    con = connect()
    out = {}
    for d in con.execute("SELECT * FROM documents WHERE n_chunks>0"):
        rows = con.execute("SELECT * FROM chunks WHERE doc_id=? ORDER BY ord", (d["doc_id"],)).fetchall()
        out[d["doc_id"]] = [{"doc_id": d["doc_id"], "chunk_id": r["chunk_id"], "location": r["location"],
                             "text": clean(r["text"])[:MAX_CHARS], "title": d["title"],
                             "publication_date": d["publication_date"] or None} for r in rows]
    return out


def rechunk(doc_passages: list[dict], size: int) -> list[dict]:
    """Augmentation: re-chunk a document's text at different boundaries (train only)."""
    import app.ingestion.documents as D
    old = D.CHUNK_CHARS
    D.CHUNK_CHARS = size
    try:
        secs = [(p["location"], p["text"]) for p in doc_passages]
        joined = []
        for loc, t in secs:
            if joined and joined[-1][0] == loc:
                joined[-1] = (loc, joined[-1][1] + "\n\n" + t)
            else:
                joined.append((loc, t))
        chs = chunk(joined)
    finally:
        D.CHUNK_CHARS = old
    base = doc_passages[0]
    return [{**base, "chunk_id": f"{base['doc_id']}#r{size}-{i:03d}", "location": loc, "text": t[:MAX_CHARS]}
            for i, (loc, t) in enumerate(chs)]


def msg_A(p: dict, instr: str) -> dict:
    gold = spec.label(p["text"])
    return {"task": "A", "messages": [
        {"role": "system", "content": spec.SYSTEM},
        {"role": "user", "content": f"{instr}\n\nPASSAGE:\n{p['text']}"},
        {"role": "assistant", "content": spec.to_lines(gold)}],
        "gold": gold, "passage": p["text"], "doc_id": p["doc_id"], "chunk_id": p["chunk_id"]}


# ---- task B: timeline (event date vs publication date) ------------------------
SYS_B = ("You reconstruct mission timelines. List each explicitly dated event as 'EVENT YYYY-MM-DD | sentence' "
         "(sentence copied verbatim), then 'PUBLISHED YYYY-MM-DD' or 'PUBLISHED ?'. Write 'EVENT ?' if no dated event.")


def gold_B(p: dict) -> str:
    lines = []
    for s in spec.sentences(p["text"]):
        for d in spec._dates(s):
            lines.append(f"EVENT {d} | {s}")
    if not lines:
        lines.append("EVENT ?")
    lines.append(f"PUBLISHED {p['publication_date'] or '?'}")
    return "\n".join(lines)


def msg_B(p: dict) -> dict:
    meta = f"DOCUMENT: {p['title']}\nPUBLICATION DATE (metadata): {p['publication_date'] or 'unknown'}"
    return {"task": "B", "messages": [
        {"role": "system", "content": SYS_B},
        {"role": "user", "content": f"{meta}\n\nPASSAGE:\n{p['text']}"},
        {"role": "assistant", "content": gold_B(p)}], "passage": p["text"], "doc_id": p["doc_id"],
        "chunk_id": p["chunk_id"], "publication_date": p["publication_date"]}


# ---- task C: terminology with sources ------------------------------------------
SYS_C = ("You explain OPS-SAT telemetry terms using ONLY the numbered sources. Answer: 'DEFINITION: <one sentence "
         "copied verbatim from a source>' and 'SOURCE: [n]'. If no source defines the term: 'DEFINITION: ?' and 'SOURCE: none'.")


def build_C(all_passages: list[dict], split: str) -> list[dict]:
    terms = list(CHANNELS) + [v[0] for v in CHANNELS.values()] + [
        "gaps_squared", "n_peaks", "smooth10_n_peaks", "diff_var", "len_weighted", "var_div_duration",
        "kurtosis", "sampling", "anomaly", "segment", "magnetometer", "photodiode"]
    out = []
    for term in terms:
        hits = [p for p in all_passages if re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", p["text"])]
        others = [p for p in all_passages if p not in hits]
        for variant in ("present", "absent"):
            if variant == "present" and not hits:
                continue
            ctx = ([RNG.choice(hits)] if variant == "present" else []) + RNG.sample(others, min(2, len(others)))
            RNG.shuffle(ctx)
            src_idx, sent = None, None
            for i, p in enumerate(ctx, 1):
                if variant == "present" and p in hits:
                    sent = next((s for s in spec.sentences(p["text"])
                                 if re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", s)), None)
                    src_idx = i if sent else None
            ans = f"DEFINITION: {sent}\nSOURCE: [{src_idx}]" if sent else "DEFINITION: ?\nSOURCE: none"
            srcs = "\n\n".join(f"[{i}] ({p['chunk_id']}) {p['text'][:700]}" for i, p in enumerate(ctx, 1))
            out.append({"task": "C", "term": term, "variant": variant, "messages": [
                {"role": "system", "content": SYS_C},
                {"role": "user", "content": f"TERM: {term}\n\nSOURCES:\n{srcs}"},
                {"role": "assistant", "content": ans}], "gold_source": src_idx,
                "sources": [p["chunk_id"] for p in ctx], "gold_sentence": sent})
    return out


# ---- task D: investigation report ---------------------------------------------
SYS_D = ("You write investigation notes for archived OPS-SAT telemetry. Use only the MEASUREMENTS, MODEL and SOURCES given. "
         "Output sections: KNOWN (bullets, each ending with [measured] or [n]), UNKNOWN (bullets), ACTION (one line). "
         "Never state a root cause unless a source states it explicitly; otherwise list it under UNKNOWN.")


def gold_D(ev: dict, prob: float, decision: str, cites: list[dict]) -> str:
    known = [f"- Model probability of anomaly is {prob:.2f} (decision: {decision}). [measured]"]
    if ev["max_zero_run"] > 1:
        known.append(f"- The segment contains {ev['zero_runs']} run(s) of exact zeros; the longest is {ev['max_zero_run']} samples. [measured]")
    if ev["gap_count"] > 0:
        known.append(f"- There are {ev['gap_count']} sampling gap(s); the longest is {ev['max_gap_s']:.0f} s. [measured]")
    known.append(f"- The signal has {ev['n_peaks']} prominent peak(s). [measured]")
    for i, c in enumerate(cites, 1):
        if c.get("relevant"):
            known.append(f"- {c['sentence']} [{i}]")
    unknown = ["- The root cause of this signal behaviour is not documented in the provided sources."]
    if not any(c.get("relevant") for c in cites):
        unknown.append("- No provided source describes this type of signal behaviour.")
    action = {"prioritise": "Prioritise for analyst review.", "queue": "Queue for routine analyst review.",
              "archive": "Archive; no review needed unless new evidence appears."}[decision]
    return "KNOWN\n" + "\n".join(known) + "\nUNKNOWN\n" + "\n".join(unknown) + f"\nACTION\n{action}"


def build_D(split_segments: list[int], all_passages: list[dict], n: int) -> list[dict]:
    import pandas as pd
    from app.telemetry.evidence import signal_evidence
    con = connect()
    preds = dict(con.execute("SELECT segment_id, probability FROM predictions").fetchall())
    thr_hi, thr_lo = 0.6, 0.3
    try:
        thr = json.loads((DATA_PROCESSED.parent.parent / "evaluations" / "thresholds.json").read_text())
        thr_hi, thr_lo = thr["high"], thr["low"]
    except Exception:
        pass
    taxonomy = [p for p in all_passages if re.search(r"zero|gap|peak", p["text"], re.I)]
    out = []
    for sid in RNG.sample(split_segments, min(n, len(split_segments))):
        if sid not in preds:
            continue
        df = pd.read_sql("SELECT timestamp, value FROM telemetry_points WHERE segment_id=? ORDER BY idx", con, params=(sid,))
        samp = con.execute("SELECT sampling FROM segments WHERE segment_id=?", (sid,)).fetchone()[0]
        ev = signal_evidence(df["timestamp"], df["value"].to_numpy(), samp)
        prob = preds[sid]
        decision = "prioritise" if prob >= thr_hi else "queue" if prob >= thr_lo else "archive"
        ctx = RNG.sample(taxonomy, 1) + RNG.sample(all_passages, 1)
        cites = []
        for p in ctx:
            s = next((s for s in spec.sentences(p["text"]) if re.search(r"zero|gap|peak", s, re.I)), None)
            cites.append({"chunk_id": p["chunk_id"], "text": p["text"][:600], "relevant": bool(s), "sentence": s})
        meas = (f"zero_runs={ev['zero_runs']} max_zero_run={ev['max_zero_run']} gap_count={ev['gap_count']} "
                f"max_gap_s={ev['max_gap_s']:.0f} n_peaks={ev['n_peaks']} noise_std={ev['noise_std']:.3g}")
        srcs = "\n\n".join(f"[{i}] ({c['chunk_id']}) {c['text']}" for i, c in enumerate(cites, 1))
        out.append({"task": "D", "segment_id": int(sid), "messages": [
            {"role": "system", "content": SYS_D},
            {"role": "user", "content": f"MEASUREMENTS: {meas}\nMODEL: P(anomalous)={prob:.2f}, decision={decision}\n\nSOURCES:\n{srcs}"},
            {"role": "assistant", "content": gold_D(ev, prob, decision, cites)}],
            "evidence": ev, "probability": prob, "decision": decision, "cites": cites})
    return out


# ---- templated augmentation (train split only, provenance-tagged) -------------
def templated_A(n: int) -> list[dict]:
    chans = list(CHANNELS.items())
    obs_t = ["the {name} channel ({cid}) showed an unexpected run of zero values lasting {k} samples.",
             "telemetry from {cid} contained {k} gaps between consecutive samples.",
             "the {kind} signal on {name} exhibited unusual peaks above the nominal envelope.",
             "operators noted degraded readings from the {kind} {cid}."]
    resp_t = ["Operators commanded a reboot of the payload computer.", "The team performed a recovery of the attitude subsystem.",
              "The instrument was switched off for the remainder of the pass.", None, None]
    cause_t = ["The readings were caused by a saturated sensor during eclipse exit.",
               "The gaps resulted in the loss of {k} minutes of housekeeping data.",
               "The cause may have been a software timing fault, but this was not confirmed.",
               "It is unclear what triggered the zero values.", None, None]
    units_t = ["", " Values are reported in nT.", " Sampling was set to {s} seconds.", " Angles are given in degrees."]
    out = []
    list_t = ["The {kind} channels {a} ({ia}) and {b} ({ib}) were sampled at {s} s.",
              "Telemetry was acquired from {ia}, {ib} and {ic}.",
              "Table 1 lists {a}, {b} and {c} as {kind} readings.",
              "Segments from the {kind} {ia} were annotated by operations engineers."]
    for i in range(n // 3):
        kind = RNG.choice(["magnetometer", "photodiode"])
        pool = [(c, v[0]) for c, v in chans if v[1] == kind]
        (ia, a), (ib, b), (ic, c) = RNG.sample(pool, 3)
        text = RNG.choice(list_t).format(kind=kind, a=a, b=b, c=c, ia=ia, ib=ib, ic=ic, s=RNG.choice([1, 5]))
        if RNG.random() < 0.5:
            text += " " + RNG.choice(["No anomalies were reported for these channels.",
                                      "Some segments contain gaps in the signal.",
                                      "The origin of the zero-value fragments is not described."])
        p = {"doc_id": "templated", "chunk_id": f"templated#L{i:03d}", "text": text}
        ex = msg_A(p, RNG.choice(spec.INSTRUCTIONS)); ex["provenance"] = "templated"
        out.append(ex)
    for i in range(n - n // 3):
        cid, (name, kind) = RNG.choice(chans)
        k = RNG.randint(2, 60)
        day = f"{RNG.randint(1, 28)} {RNG.choice(spec.MONTHS.split('|'))} {RNG.choice([2020, 2021, 2022, 2023])}"
        parts = [f"On {day}, " + RNG.choice(obs_t).format(name=name, cid=cid, kind=kind, k=k)]
        r = RNG.choice(resp_t)
        if r:
            parts.append(r)
        c = RNG.choice(cause_t)
        if c:
            parts.append(c.format(k=k))
        text = " ".join(parts) + RNG.choice(units_t).format(s=RNG.choice([1, 5]))
        p = {"doc_id": "templated", "chunk_id": f"templated#{i:03d}", "text": text}
        ex = msg_A(p, RNG.choice(spec.INSTRUCTIONS))
        ex["provenance"] = "templated"
        out.append(ex)
    return out


def main(n_templated: int = 120):
    docs = passages_by_doc()
    splits = {"train": [], "val": [], "test": []}
    passages_split = {"train": [], "val": [], "test": []}
    for doc_id, ps in docs.items():
        if doc_id in EXCLUDE:
            continue
        fam = FAMILY.get(doc_id, doc_id)
        sp = SPLIT.get(fam)
        if sp is None:
            continue
        passages_split[sp] += ps
        for p in ps:
            instr = spec.INSTRUCTIONS[0] if sp != "train" else RNG.choice(spec.INSTRUCTIONS)
            ex = msg_A(p, instr); ex["provenance"] = "real"
            splits[sp].append(ex)
        if sp == "train" and len(ps) > 3:
            for size in (500, 1100):
                for p in RNG.sample(rechunk(ps, size), min(25, len(rechunk(ps, size)))):
                    ex = msg_A(p, RNG.choice(spec.INSTRUCTIONS)); ex["provenance"] = "real-rechunked"
                    splits["train"].append(ex)
    for sp in splits:
        for p in passages_split[sp]:
            if spec._dates(p["text"]) or RNG.random() < 0.25:
                ex = msg_B(p); ex["provenance"] = "real"; splits[sp].append(ex)
        for ex in build_C(passages_split[sp], sp):
            ex["provenance"] = "real"; splits[sp].append(ex)
    con = connect()
    seg = {sp: [r[0] for r in con.execute("SELECT segment_id FROM segments WHERE split=?",
                                           ("train" if sp != "test" else "test",))] for sp in splits}
    RNG.shuffle(seg["train"])
    seg_train, seg_val = seg["train"][:1300], seg["train"][1300:]
    for sp, ids, n in (("train", seg_train, 40), ("val", seg_val, 15), ("test", seg["test"], 25)):
        for ex in build_D(ids, passages_split[sp], n):
            ex["provenance"] = "real"; splits[sp].append(ex)
    tmpl = templated_A(n_templated + 30)
    splits["train"] += tmpl[:n_templated]
    splits["val"] += tmpl[n_templated:]      # held-out templated examples for VAL iteration only (never test)
    # dedupe train against held-out passages (exact or containment)
    held = [norm(e.get("passage", "")) for sp in ("val", "test") for e in splits[sp] if e.get("passage")]
    before = len(splits["train"])
    splits["train"] = [e for e in splits["train"] if not e.get("passage") or
                       not any(norm(e["passage"])[:200] in h or h[:200] in norm(e["passage"]) for h in held if h)]
    RNG.shuffle(splits["train"])
    for sp, rows in splits.items():
        with open(OUT / f"{sp}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    stats = {sp: {"total": len(r), **{f"task_{t}": sum(1 for x in r if x["task"] == t) for t in "ABCD"},
                  "provenance": {pv: sum(1 for x in r if x.get("provenance") == pv) for pv in
                                 {x.get("provenance") for x in r}}} for sp, r in splits.items()}
    stats["dedup_removed_from_train"] = before - len(splits["train"])
    stats["split_by_family"] = SPLIT
    gold_A = [x["gold"] for x in splits["test"] if x["task"] == "A"]
    stats["test_A_field_coverage"] = {f: sum(1 for g in gold_A if g[f]) for f in spec.FIELDS}
    write_eval_json("sft_dataset_stats.json", stats, "python -m training.tinker.prepare_sft")
    print(json.dumps({k: v for k, v in stats.items() if k in ("train", "val", "test", "test_A_field_coverage")}, indent=1))


def norm(s):
    return " ".join(s.split())


if __name__ == "__main__":
    main()
