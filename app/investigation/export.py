"""Mission memory archive export: a zip bundle of documents (licence-permitted text only), extracted records,
investigation cards, evidence, feedback, evaluation artefacts and a manifest."""
from __future__ import annotations

import io
import json
import zipfile

from app.common.paths import DOCS_DIR, EVAL_DIR, ROOT, git_sha, now_iso
from app.memory.db import connect


def build_zip() -> bytes:
    con = connect()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        docs = [dict(r) for r in con.execute("SELECT * FROM documents")]
        z.writestr("documents/index.json", json.dumps(docs, indent=1))
        for d in docs:
            chunks = [dict(r) for r in con.execute("SELECT chunk_id, location, text FROM chunks WHERE doc_id=? ORDER BY ord", (d["doc_id"],))]
            z.writestr(f"documents/{d['doc_id']}.json", json.dumps({"document": d, "stored_mode": d["stored_mode"],
                                                                     "chunks": chunks}, indent=1))
        z.writestr("records/records.json", json.dumps([dict(r) for r in con.execute("SELECT * FROM records")], indent=1))
        cards = [dict(r) for r in con.execute("SELECT * FROM investigations")]
        z.writestr("investigations/cards.json", json.dumps(cards, indent=1))
        z.writestr("investigations/feedback.json", json.dumps([dict(r) for r in con.execute("SELECT * FROM feedback")], indent=1))
        z.writestr("predictions/predictions.json", json.dumps([dict(r) for r in con.execute("SELECT * FROM predictions")]))
        for p in EVAL_DIR.iterdir():
            if p.is_file():
                z.write(p, f"evaluations/{p.name}")
        z.write(ROOT / "docs" / "provenance.csv", "provenance.csv")
        tl = DOCS_DIR / "timeline.yaml"
        if tl.exists():
            z.write(tl, "timeline.yaml")
        z.writestr("MANIFEST.json", json.dumps({
            "name": "The Last Satellite: mission memory archive (OPS-SAT, archival)",
            "created_at": now_iso(), "git_sha": git_sha(),
            "contents": ["documents/", "records/", "investigations/", "predictions/", "evaluations/", "provenance.csv", "timeline.yaml"],
            "licensing": {"telemetry": "OPSSAT-AD, CC-BY-4.0 (not redistributed here; see Zenodo 10.5281/zenodo.12588359)",
                          "documents": "full text only where the licence permits (CC-BY / CC-BY-SA / MIT); others are short excerpts + links",
                          "code": "see LICENSE"},
            "note": "OPS-SAT re-entered on 22 May 2024. This is an archival analysis, not live telemetry."}, indent=1))
    return buf.getvalue()


if __name__ == "__main__":
    out = ROOT / "data" / "processed" / "mission_memory_archive.zip"
    out.write_bytes(build_zip())
    print(out, out.stat().st_size, "bytes")
