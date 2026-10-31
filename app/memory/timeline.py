"""Build the mission timeline from verified quotes (task-B ground truth for the UI)."""
from __future__ import annotations

import yaml

from app.common.paths import DOCS_DIR
from app.memory.db import connect


def norm(s: str) -> str:
    return " ".join(s.split())


def build() -> list[dict]:
    con = connect()
    items = yaml.safe_load((DOCS_DIR / "timeline_sources.yaml").read_text())
    out = []
    for it in items:
        cit = None
        if it.get("doc_id"):
            d = con.execute("SELECT * FROM documents WHERE doc_id=?", (it["doc_id"],)).fetchone()
            if d is None:
                continue
            if it.get("quote"):
                hit = None
                for c in con.execute("SELECT * FROM chunks WHERE doc_id=?", (it["doc_id"],)):
                    if norm(it["quote"]) in norm(c["text"]):
                        hit = c
                        break
                if hit is None:
                    print("DROPPED (quote not verified):", it["title"])
                    continue
                cit = {"doc_id": d["doc_id"], "chunk_id": hit["chunk_id"], "title": d["title"], "url": d["url"],
                       "location": hit["location"], "excerpt": it["quote"], "license": d["license"]}
            else:
                cit = {"doc_id": d["doc_id"], "chunk_id": None, "title": d["title"], "url": d["url"],
                       "location": "publication metadata", "excerpt": "", "license": d["license"]}
        out.append({"date": str(it["date"]), "date_kind": it["date_kind"], "approx": it.get("approx"),
                    "title": it["title"], "citation": cit, "measured": it.get("measured")})
    (DOCS_DIR / "timeline.yaml").write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))
    return out


if __name__ == "__main__":
    print(len(build()), "verified timeline entries")
