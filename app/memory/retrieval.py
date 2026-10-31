"""Hybrid retrieval: SQLite FTS5 (BM25) + dense embeddings, fused with reciprocal-rank fusion.
Every hit is returned as a Citation-shaped dict carrying a verbatim excerpt and its source."""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np

from app.common.config import load_config
from app.memory.db import connect


@lru_cache
def embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(load_config()["retrieval"]["embedding_model"], device="cpu")


@lru_cache
def _matrix():
    con = connect()
    rows = con.execute("SELECT chunk_id, vec FROM chunk_vectors").fetchall()
    if not rows:
        return [], np.zeros((0, 1), dtype=np.float32)
    return [r["chunk_id"] for r in rows], np.vstack([np.frombuffer(r["vec"], dtype=np.float32) for r in rows])


def _fts_query(q: str) -> str:
    toks = [t for t in re.findall(r"[A-Za-z0-9_]+", q) if len(t) > 2]
    return " OR ".join(f'"{t}"' for t in toks) or '""'


def search(query: str, k: int = 6, rrf_k: int = 60) -> list[dict]:
    con = connect()
    bm25 = [r["chunk_id"] for r in con.execute(
        "SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT 30",
        (_fts_query(query),)).fetchall()]
    ids, M = _matrix()
    dense = []
    if len(ids):
        qv = embedder().encode([query], normalize_embeddings=True)[0].astype(np.float32)
        sims = M @ qv
        dense = [ids[i] for i in np.argsort(-sims)[:30]]
    scores: dict[str, float] = {}
    for ranking in (bm25, dense):
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
    top = sorted(scores.items(), key=lambda x: -x[1])[:k]
    out = []
    for cid, s in top:
        r = con.execute("SELECT c.chunk_id, c.doc_id, c.location, c.text, d.title, d.url, d.license "
                        "FROM chunks c JOIN documents d USING(doc_id) WHERE c.chunk_id=?", (cid,)).fetchone()
        out.append({"doc_id": r["doc_id"], "chunk_id": r["chunk_id"], "title": r["title"], "url": r["url"],
                    "location": r["location"], "excerpt": r["text"], "score": round(s, 4),
                    "license": r["license"]})
    return out
