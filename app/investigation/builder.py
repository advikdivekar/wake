"""Evidence Integration Layer -> Investigation Card.

Raw measurements, the model prediction, retrieved documents, similar segments and the generated summary
are stored in SEPARATE columns so every statement on the card is traceable. A root cause is never
asserted unless a retrieved source states one explicitly; otherwise it is listed under "unknown".
"""
from __future__ import annotations

import json
import re

from app.common.paths import now_iso
from app.memory.db import connect
from app.memory.retrieval import search
from app.memory.similar import similar
from app.prediction.service import predict_segment
from app.telemetry.evidence import signal_evidence
from training.tinker import spec
from training.tinker.prepare_sft import SYS_D

CAUSE_CLAIM = re.compile(r"\b(caused by|due to|because|root cause|resulted from|triggered by)\b", re.I)
SIGNAL_TERMS = re.compile(r"zero|gap|peak|anomal|spike", re.I)


def _query(seg: dict, ev: dict) -> str:
    bits = [seg["channel_kind"] or "", "anomalous telemetry segments unusual signal shapes"]
    if ev["max_zero_run"] > 1:
        bits.append("signal fragments with zero values")
    if ev["gap_count"]:
        bits.append("gaps in the signal")
    if ev["n_peaks"] > 2:
        bits.append("single or multiple peaks")
    return " ".join(bits)


def _cited_sentences(cites: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(cites, 1):
        s = next((s for s in spec.sentences(c["excerpt"])
                  if SIGNAL_TERMS.search(s) and re.match(r"^[A-Z][a-z]", s) and 50 <= len(s) <= 350
                  and not re.match(r"^(Abstract|Fig|Table)", s)), None)
        out.append({**c, "sentence": s, "relevant": bool(s), "n": i})
    return out


def _template_summary(pred, ev, cites) -> str:
    parts = [f"TabPFN assigns P(anomalous) = {pred['probability']:.2f} ({pred['decision']})."]
    if ev["max_zero_run"] > 1:
        parts.append(f"The archived segment contains {ev['zero_runs']} exact-zero run(s), longest {ev['max_zero_run']} samples.")
    if ev["gap_count"]:
        parts.append(f"It has {ev['gap_count']} sampling gap(s), longest {ev['max_gap_s']:.0f} s.")
    rel = [c for c in cites if c["relevant"]]
    if rel:
        parts.append(f"The archive describes similar signal behaviour as an annotated anomaly type [{rel[0]['n']}].")
    parts.append("The archive does not document a root cause for this segment.")
    return " ".join(parts)


def build_card(segment_id: int, use_lm: bool = True) -> dict:
    con = connect()
    seg = dict(con.execute("SELECT * FROM segments WHERE segment_id=?", (segment_id,)).fetchone())
    pts = con.execute("SELECT timestamp, value FROM telemetry_points WHERE segment_id=? ORDER BY idx", (segment_id,)).fetchall()
    ev = signal_evidence([p[0] for p in pts], [p[1] for p in pts], seg["sampling"])
    pred = predict_segment(segment_id)
    hits = search(_query(seg, ev), k=4)
    cites = _cited_sentences(hits)
    sim = similar(segment_id, 5)

    known = [{"statement": f"TabPFN probability of anomaly is {pred['probability']:.2f}; decision '{pred['decision']}' "
                           f"(thresholds {pred['thresholds']['low']}/{pred['thresholds']['high']} chosen on training data).",
              "basis": "measured", "citations": []}]
    if ev["max_zero_run"] > 1:
        known.append({"statement": f"{ev['zero_runs']} run(s) of exact zeros; longest {ev['max_zero_run']} samples.",
                      "basis": "measured", "citations": []})
    if ev["gap_count"]:
        known.append({"statement": f"{ev['gap_count']} sampling gap(s); longest {ev['max_gap_s']:.0f} s.",
                      "basis": "measured", "citations": []})
    known.append({"statement": f"{ev['n_peaks']} prominent peak(s); sample-to-sample noise std {ev['noise_std']:.3g}.",
                  "basis": "measured", "citations": []})
    seen = set()
    for c in cites:
        if c["relevant"] and c["sentence"] not in seen:
            seen.add(c["sentence"])
            known.append({"statement": c["sentence"], "basis": "cited",
                          "citations": [{k: c[k] for k in ("doc_id", "chunk_id", "title", "url", "location", "score", "license")}
                                        | {"excerpt": c["sentence"]}]})
    n_anom = sum(s["label"] for s in sim)
    known.append({"statement": f"{n_anom} of the {len(sim)} most similar training segments were labelled anomalous "
                               "(resemblance, not a shared fault).", "basis": "measured", "citations": []})
    # A cause applies to THIS segment only if a source explicitly ties it to this channel AND this date.
    day = seg["start"][:10]
    names = {seg["channel"], seg["channel_name"]}
    stated_causes = [c for c in cites if c["relevant"] and CAUSE_CLAIM.search(c["sentence"])
                     and not spec.HEDGES.search(c["sentence"])
                     and any(n and n in c["sentence"] for n in names) and day in spec._dates(c["sentence"])]
    unknown = []
    if not stated_causes:
        unknown.append("Root cause of this signal behaviour is not documented in the archive.")
    unknown.append("Whether operators acted on this specific segment is not recorded in the archive.")
    if not any(c["relevant"] for c in cites):
        unknown.append("No archived document describes this type of signal behaviour.")

    summary, model_name = _template_summary(pred, ev, cites), "template (deterministic)"
    if use_lm:
        try:
            from app.investigation.lm import get_lm
            lm = get_lm()
            if lm.name.startswith("template"):
                raise RuntimeError("template backend")
            meas = (f"zero_runs={ev['zero_runs']} max_zero_run={ev['max_zero_run']} gap_count={ev['gap_count']} "
                    f"max_gap_s={ev['max_gap_s']:.0f} n_peaks={ev['n_peaks']} noise_std={ev['noise_std']:.3g}")
            srcs = "\n\n".join(f"[{c['n']}] ({c['chunk_id']}) {c['excerpt'][:600]}" for c in cites[:2])
            out = lm.chat([{"role": "system", "content": SYS_D},
                           {"role": "user", "content": f"MEASUREMENTS: {meas}\nMODEL: P(anomalous)={pred['probability']:.2f}, "
                                                       f"decision={pred['decision']}\n\nSOURCES:\n{srcs}"}], max_tokens=400)
            known_part = out.split("UNKNOWN")[0]
            cited_ok = all(1 <= int(n) <= 2 for n in re.findall(r"\[(\d+)\]", out))
            if "KNOWN" in out and "UNKNOWN" in out and cited_ok and not CAUSE_CLAIM.search(known_part):
                summary, model_name = out.strip(), lm.name
            else:
                model_name = f"template (LM output rejected by validator: {lm.name})"
        except Exception as e:  # LM unavailable -> deterministic template, recorded as such
            model_name = f"template (LM unavailable: {type(e).__name__})"

    action = {"prioritise": "Prioritise for analyst review.", "queue": "Queue for routine analyst review.",
              "archive": "Archive; review only if new evidence appears."}[pred["decision"]]
    n = con.execute("SELECT COUNT(*) FROM investigations WHERE segment_id=?", (segment_id,)).fetchone()[0]
    card_id = f"inv-{segment_id}-{n + 1}"
    documents = [{k: c[k] for k in ("doc_id", "chunk_id", "title", "url", "location", "excerpt", "score", "license")} for c in cites]
    con.execute("INSERT INTO investigations(card_id, segment_id, created_at, evidence_json, prediction_json, documents_json, "
                "similar_json, known_json, unknown_json, summary, summary_model, suggested_action) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (card_id, segment_id, now_iso(), json.dumps(ev), json.dumps(pred), json.dumps(documents), json.dumps(sim),
                 json.dumps(known), json.dumps(unknown), summary, model_name, action))
    con.commit()
    return get_card(card_id)


def get_card(card_id: str) -> dict | None:
    con = connect()
    r = con.execute("SELECT * FROM investigations WHERE card_id=?", (card_id,)).fetchone()
    if r is None:
        return None
    gt = None
    if r["revealed"]:
        gt = con.execute("SELECT label FROM segments WHERE segment_id=?", (r["segment_id"],)).fetchone()[0]
    pred = json.loads(r["prediction_json"])
    pred.pop("source", None)
    return {"card_id": r["card_id"], "segment_id": r["segment_id"], "created_at": r["created_at"],
            "prediction": pred, "signal_evidence": json.loads(r["evidence_json"]),
            "historical_context": json.loads(r["similar_json"]), "documents": json.loads(r["documents_json"]),
            "known": json.loads(r["known_json"]), "unknown": json.loads(r["unknown_json"]),
            "suggested_action": r["suggested_action"], "summary": r["summary"], "summary_model": r["summary_model"],
            "review_status": r["review_status"], "ground_truth": gt}


def list_cards(status: str | None = None) -> list[dict]:
    q, p = "SELECT card_id FROM investigations", []
    if status:
        q += " WHERE review_status=?"; p.append(status)
    return [get_card(r[0]) for r in connect().execute(q + " ORDER BY created_at DESC", p).fetchall()]


def feedback(card_id: str, action: str, note: str) -> dict | None:
    con = connect()
    if con.execute("SELECT 1 FROM investigations WHERE card_id=?", (card_id,)).fetchone() is None:
        return None
    status = {"confirm": "confirmed", "reject": "rejected", "investigate": "investigating"}[action]
    con.execute("INSERT INTO feedback(card_id, action, note, at) VALUES (?,?,?,?)", (card_id, action, note, now_iso()))
    con.execute("UPDATE investigations SET review_status=? WHERE card_id=?", (status, card_id))
    con.commit()
    return get_card(card_id)


def reveal(card_id: str) -> dict | None:
    con = connect()
    con.execute("UPDATE investigations SET revealed=1 WHERE card_id=?", (card_id,))
    con.commit()
    return get_card(card_id)
