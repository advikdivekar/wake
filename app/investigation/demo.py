"""Demo set for 'The signal that should not be there': real TEST segments covering TP, TN, FP and FN.
Cases are chosen from the final model's test predictions at the max-F1 threshold (chosen on training OOF)."""
from __future__ import annotations

import json

from app.common.paths import DATA_PROCESSED, EVAL_DIR
from app.memory.db import connect

PATH = DATA_PROCESSED / "demo_set.json"


def build() -> list[dict]:
    con = connect()
    thr = json.loads((EVAL_DIR / "thresholds.json").read_text())["f1"]
    rows = con.execute("SELECT s.segment_id, s.channel, s.channel_kind, s.label, p.probability FROM segments s "
                       "JOIN predictions p USING(segment_id) WHERE s.split='test'").fetchall()
    case = lambda r: ("TP" if r["label"] else "FP") if r["probability"] >= thr else ("FN" if r["label"] else "TN")
    by = {c: sorted([r for r in rows if case(r) == c], key=lambda r: -r["probability"]) for c in ("TP", "TN", "FP", "FN")}
    picks = by["TP"][:1] + by["TP"][len(by["TP"]) // 2: len(by["TP"]) // 2 + 1] + by["TN"][-1:] + \
        by["TN"][:1] + by["FP"][:1] + by["FN"][:1]
    out = []
    for r in picks:
        out.append({"segment_id": r["segment_id"], "case": case(r), "probability": round(r["probability"], 4),
                    "label": r["label"], "channel": r["channel"],
                    "blurb": f"Archived {r['channel_kind']} segment from {r['channel']}"})
    PATH.write_text(json.dumps({"threshold": thr, "items": out, "counts": {c: len(v) for c, v in by.items()}}, indent=1))
    return out


def load() -> dict:
    if not PATH.exists():
        build()
    return json.loads(PATH.read_text())


if __name__ == "__main__":
    print(build())
