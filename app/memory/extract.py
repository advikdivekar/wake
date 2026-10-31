"""Task A at runtime: passage -> MemoryRecord. Uses the interpreter LM when available (validated), otherwise the
deterministic spec extractor. Results are stored in the `records` table."""
from __future__ import annotations

import hashlib
import json

from app.common.paths import now_iso
from app.memory.db import connect
from training.tinker import spec


def extract(text: str, source: dict | None = None) -> dict:
    model = "rule-based spec extractor (deterministic)"
    rec = spec.label(text)
    flags = []
    try:
        from app.investigation.lm import get_lm
        lm = get_lm()
        if not lm.name.startswith("template"):
            out = lm.chat([{"role": "system", "content": spec.SYSTEM},
                           {"role": "user", "content": f"{spec.INSTRUCTIONS[0]}\n\nPASSAGE:\n{text}"}], max_tokens=400)
            parsed, errs = spec.parse_lines(out)
            if parsed is not None:
                v = spec.validate(parsed, text)
                rec, flags, model = v["record"], v["flags"] + errs, lm.name
    except Exception as e:
        flags.append(f"lm_unavailable:{type(e).__name__}")
    out = spec.to_record_json(rec, source)
    rid = "rec-" + hashlib.sha1((text + model).encode()).hexdigest()[:10]
    out["record_id"] = rid
    out["model"] = model
    out["validator_flags"] = flags
    con = connect()
    con.execute("INSERT OR REPLACE INTO records VALUES (?,?,?,?,?)",
                (rid, (source or {}).get("chunk_id"), model, json.dumps(out), now_iso()))
    con.commit()
    return out
