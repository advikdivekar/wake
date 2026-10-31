"""Task-A extraction SPEC: the deterministic labelling rules, the compact output format,
the parser (line format -> MemoryRecord JSON) and the validator. The same module produces
training targets, parses model output and scores it, so the definition is frozen in one place.
"""
from __future__ import annotations

import re
from datetime import datetime

from app.common.channels import CHANNELS

FIELDS = ["channel_id", "sensor_type", "units", "event_date", "observation",
          "operational_response", "root_cause", "evidence"]
LIST_FIELDS = {"channel_id", "sensor_type", "units", "event_date"}
SPAN_FIELDS = {"observation", "operational_response", "root_cause", "evidence"}
UNKNOWN = "?"

NAME_TO_ID = {v[0]: k for k, v in CHANNELS.items()}
CH_RE = re.compile(r"\b(CADC\d{4}|I_B_FB_MM_[0-2]|I_PD[1-6]_THETA)\b")
UNIT_RE = re.compile(r"(?<![A-Za-z])(µT|μT|nT|mT|°C|K/s|deg/s|rad/s|Hz|kHz|MHz|GHz|kbps|Mbps|km/s|km|"
                     r"seconds|milliseconds|degrees|radians|kelvin|watts|volts|amperes)(?![A-Za-z])")
UNIT_NORM = {"μT": "µT"}
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RES = [
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS}),?\s+(\d{{4}})\b"), "dmy"),
    (re.compile(rf"\b({MONTHS})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b"), "mdy"),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso"),
]
OBS_CUES = re.compile(r"\b(anomal\w*|gaps?|zero[- ]value|zeros|peaks?|spikes?|unexpected\w*|unusual|"
                      r"deteriorat\w*|degrad\w*|drag|malfunction\w*|fault\w*|failure\w*|outage\w*)\b", re.I)
RESP_CUES = re.compile(r"\b(reboot\w*|recover\w*|safe mode|restart\w*|shut ?down|commanded|"
                       r"operators? (?:should be )?notified|mitigat\w*|switched off|power[- ]cycl\w*)\b", re.I)
CAUSE_CUES = re.compile(r"\b(caused by|due to|because of|because|led to|leading to|resulted in|"
                        r"as a result of|triggered by|attributed to)\b", re.I)
HEDGES = re.compile(r"\b(may|might|possibly|likely|unlikely|unclear|unknown|suspected|could|perhaps|"
                    r"presumably|probably|not (?:yet )?(?:known|established|determined))\b", re.I)


def norm_ws(s: str) -> str:
    return " ".join(s.split())


def sentences(text: str) -> list[str]:
    t = norm_ws(text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(\[])", t)
    return [p.strip() for p in parts if len(p.strip()) > 3]


def _dates(text: str) -> list[str]:
    found = []
    for rx, kind in DATE_RES:
        for m in rx.finditer(text):
            try:
                if kind == "dmy":
                    d = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y")
                elif kind == "mdy":
                    d = datetime.strptime(f"{m.group(2)} {m.group(1)} {m.group(3)}", "%d %B %Y")
                else:
                    d = datetime.strptime(m.group(0), "%Y-%m-%d")
            except ValueError:
                continue
            found.append((m.start(), d.strftime("%Y-%m-%d")))
    out = []
    for _, d in sorted(found):
        if d not in out:
            out.append(d)
    return out


def _uniq(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def label(passage: str) -> dict:
    """Deterministic ground truth for a passage (the frozen spec)."""
    text = norm_ws(passage)
    chans = _uniq(NAME_TO_ID.get(m, m) for m in CH_RE.findall(text))
    kinds = _uniq([CHANNELS[c][1] for c in chans if c in CHANNELS] +
                  [k for k in ("magnetometer", "photodiode") if re.search(rf"\b{k}s?\b", text, re.I)])
    units = _uniq(UNIT_NORM.get(u, u) for u in UNIT_RE.findall(text))
    sents = sentences(text)
    obs = next((s for s in sents if OBS_CUES.search(s)), None)
    resp = next((s for s in sents if RESP_CUES.search(s)), None)
    cause = next((s for s in sents if CAUSE_CUES.search(s) and not HEDGES.search(s)), None)
    rec = {
        "channel_id": chans, "sensor_type": sorted(kinds), "units": units, "event_date": _dates(text),
        "observation": obs, "operational_response": resp, "root_cause": cause,
    }
    rec["evidence"] = obs or resp or cause or next(
        (s for s in sents if CH_RE.search(s) or any(_dates(s)) or UNIT_RE.search(s)), None)
    return rec


def to_lines(rec: dict) -> str:
    out = []
    for f in FIELDS:
        v = rec.get(f)
        if f in LIST_FIELDS:
            out.append(f"{f}: {', '.join(v) if v else UNKNOWN}")
        else:
            out.append(f"{f}: {v if v else UNKNOWN}")
    return "\n".join(out)


def parse_lines(text: str) -> tuple[dict | None, list[str]]:
    """Parse model output. Returns (record, errors). record is None if unrecoverable."""
    errors, rec = [], {}
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*#>]+\s*)+", "", line).replace("**", "").replace("`", "")
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip().lower().replace(" ", "_")
        if k in FIELDS and k not in rec:
            v = v.strip()
            if k in LIST_FIELDS:
                rec[k] = [] if v in ("", UNKNOWN) else [x.strip() for x in v.split(",") if x.strip()]
            else:
                rec[k] = None if v in ("", UNKNOWN) else v
    missing = [f for f in FIELDS if f not in rec]
    if missing:
        errors.append(f"missing fields: {missing}")
    if len(missing) == len(FIELDS):
        return None, errors
    for f in missing:
        rec[f] = [] if f in LIST_FIELDS else None
    return rec, errors


def to_record_json(rec: dict, source: dict | None = None) -> dict:
    """Convert to the MemoryRecord shape (app/api/schemas.py)."""
    from app.api.schemas import MemoryRecord
    unknown = [f for f in FIELDS if f != "evidence" and not rec.get(f)]
    kinds = rec.get("sensor_type") or []
    m = MemoryRecord(
        channel_id=", ".join(rec["channel_id"]) or None,
        sensor_type=", ".join(kinds) or None,
        units=", ".join(rec["units"]) or None,
        event_date=(rec["event_date"] or [None])[0],
        observation=rec["observation"], operational_response=rec["operational_response"],
        root_cause=rec["root_cause"], evidence_excerpt=rec["evidence"], unknown_fields=unknown,
        source=source,
    )
    return m.model_dump()


def validate(rec: dict, passage: str) -> dict:
    """Deterministic, reader-independent checks. Returns flags + a repaired record."""
    text = norm_ws(passage)
    flags = []
    fixed = dict(rec)
    for f in SPAN_FIELDS:
        if rec.get(f) and norm_ws(rec[f]) not in text:
            flags.append(f"{f}:not_verbatim")
            fixed[f] = None
    if rec.get("root_cause") and HEDGES.search(rec["root_cause"]):
        flags.append("root_cause:hedged")
        fixed["root_cause"] = None
    gold_ch = set(NAME_TO_ID.get(m, m) for m in CH_RE.findall(text))
    for c in rec.get("channel_id", []):
        if c not in gold_ch:
            flags.append(f"channel_id:{c}:not_in_passage")
    fixed["channel_id"] = [c for c in rec.get("channel_id", []) if c in gold_ch]
    gold_dates = set(_dates(text))
    for d in rec.get("event_date", []):
        if d not in gold_dates:
            flags.append(f"event_date:{d}:not_in_passage")
    fixed["event_date"] = [d for d in rec.get("event_date", []) if d in gold_dates]
    return {"flags": flags, "record": fixed}


def field_equal(f: str, pred, gold) -> bool:
    if f in LIST_FIELDS:
        return list(pred or []) == list(gold or [])
    return (norm_ws(pred) if pred else None) == (norm_ws(gold) if gold else None)


SYSTEM = ("You extract structured records from OPS-SAT mission documents. Output exactly these 8 lines, in order: "
          "channel_id, sensor_type, units, event_date, observation, operational_response, root_cause, evidence "
          "(format 'field: value'). channel_id uses CADC#### ids; sensor_type is magnetometer or photodiode; "
          "event_date is YYYY-MM-DD; lists are comma-separated. Text fields copy ONE sentence verbatim from the "
          "passage. Use ? when the passage does not state it. Never infer a root cause.")
INSTRUCTIONS = [
    "Extract the mission memory record from this passage.",
    "Read the passage and fill in the record fields.",
    "Convert this archival passage into a structured record.",
    "Extract channel, sensor, units, dates, observation, response, cause and evidence.",
]
