"""Fetch public OPS-SAT documents, respect licensing, chunk with locations, index (FTS5 + vectors).

Usage: python -m app.ingestion.documents [--no-fetch]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import time

import numpy as np
import requests
import yaml

from app.common.paths import DOCS_DIR, ROOT, now_iso
from app.memory.db import init_db

UA = {"User-Agent": "TheLastSatellite/0.1 (archival research; hackathon project)"}
CACHE = DOCS_DIR / "_cache"           # raw fetched text (git-ignored); excerpt-mode text never leaves it
CACHE.mkdir(parents=True, exist_ok=True)
EXCERPT_CHARS, EXCERPT_MAX = 300, 10
CHUNK_CHARS = 800


def _arxiv_license(abs_url: str) -> str | None:
    html = requests.get(abs_url, headers=UA, timeout=30).text
    m = re.search(r'href="(https?://creativecommons\.org/licenses/[^"]+)"', html)
    if m:
        lic = m.group(1).rstrip("/").split("/licenses/")[1]
        return "CC-" + lic.split("/")[0].upper() + "-" + lic.split("/")[1]
    return None


def fetch_text(src: dict) -> list[tuple[str, str]]:
    """Return a list of (location, text) sections."""
    url = src.get("fetch_url") or src["url"]
    if "fullTextXML" in url:
        return _jats_sections(requests.get(url, headers=UA, timeout=60).text)
    if "arxiv.org/abs/" in url:
        url = url.replace("/abs/", "/pdf/")
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if url.endswith(".pdf") or "pdf" in ctype or "arxiv.org/pdf" in url:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(r.content))
        return [(f"p.{i + 1}", (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    if url.endswith(".ipynb"):
        nb = json.loads(r.text)
        out = []
        for i, c in enumerate(nb["cells"]):
            txt = "".join(c.get("source", []))
            if txt.strip():
                out.append((f"cell {i} ({c['cell_type']})", txt))
        return out
    if url.endswith(".md"):
        return _split_markdown(r.text)
    import trafilatura
    txt = trafilatura.extract(r.text, include_comments=False, include_tables=True, output_format="markdown") or ""
    return _split_markdown(txt)


def _jats_sections(xml: str) -> list[tuple[str, str]]:
    """Parse Europe PMC JATS XML into (section title, text) pairs, including table captions/cells."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    out = []
    abstract = root.find(".//abstract")
    if abstract is not None:
        out.append(("§ Abstract", " ".join("".join(abstract.itertext()).split())))

    def walk(sec, prefix=""):
        title = (sec.findtext("title") or "").strip()
        loc = "§ " + (prefix + " / " if prefix else "") + title if title else "§ " + prefix
        paras = []
        for child in sec:
            if child.tag == "p":
                paras.append(" ".join("".join(child.itertext()).split()))
            elif child.tag == "table-wrap":
                cap = " ".join("".join(child.find("caption").itertext()).split()) if child.find("caption") is not None else ""
                rows = [" | ".join(" ".join("".join(td.itertext()).split()) for td in tr) for tr in child.iter("tr")]
                paras.append(f"{child.findtext('label') or 'Table'}: {cap}\n" + "\n".join(rows))
            elif child.tag == "fig":
                cap = " ".join("".join(child.itertext()).split())
                paras.append(cap)
        if paras:
            out.append((loc.strip(), "\n\n".join(paras)))
        for sub in sec.findall("sec"):
            walk(sub, title)
    body = root.find(".//body")
    if body is not None:
        for sec in body.findall("sec"):
            walk(sec)
        loose = [" ".join("".join(p.itertext()).split()) for p in body.findall("p")]
        if loose:
            out.append(("§ Body", "\n\n".join(loose)))
    return out


def _split_markdown(txt: str) -> list[tuple[str, str]]:
    sections, cur_head, buf = [], "intro", []
    for line in txt.splitlines():
        if re.match(r"^#{1,4} ", line):
            if buf:
                sections.append((cur_head, "\n".join(buf)))
            cur_head, buf = "§ " + line.lstrip("#").strip()[:80], []
        else:
            buf.append(line)
    if buf:
        sections.append((cur_head, "\n".join(buf)))
    return sections


def chunk(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out = []
    for loc, text in sections:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        buf = ""
        for p in paras:
            p = re.sub(r"[ \t]+", " ", p)
            if len(buf) + len(p) > CHUNK_CHARS and buf:
                out.append((loc, buf.strip())); buf = ""
            while len(p) > CHUNK_CHARS * 1.5:   # hard-wrap very long paragraphs at sentence ends
                cut = p.rfind(". ", 0, CHUNK_CHARS) + 1 or CHUNK_CHARS
                out.append((loc, p[:cut].strip())); p = p[cut:].strip()
            buf += p + "\n\n"
        if buf.strip():
            out.append((loc, buf.strip()))
    return [(l, t) for l, t in out if len(t) > 40]


def excerpts(chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Excerpt mode: keep the first EXCERPT_CHARS of up to EXCERPT_MAX chunks, cut at a sentence end."""
    out = []
    for loc, t in chunks[:EXCERPT_MAX]:
        e = t[:EXCERPT_CHARS]
        if len(t) > EXCERPT_CHARS:
            cut = e.rfind(". ")
            e = e[: cut + 1] if cut > 80 else e
        out.append((loc, e))
    return out


def ingest(fetch: bool = True) -> list[dict]:
    sources = yaml.safe_load((DOCS_DIR / "sources.yaml").read_text())
    con = init_db()
    for t in ("documents", "chunks", "chunks_fts", "chunk_vectors"):
        con.execute(f"DELETE FROM {t}")
    prov = []
    for src in sources:
        doc_id, mode, lic = src["doc_id"], src["stored_mode"], src["license"]
        cache = CACHE / f"{doc_id}.json"
        status = "ok"
        try:
            if mode == "meta":
                sections = []
            elif fetch or not cache.exists():
                if lic == "detect-arxiv":
                    lic = _arxiv_license(src["url"]) or "arXiv non-exclusive licence"
                    if not lic.startswith("CC-"):
                        mode = "excerpt"
                sections = fetch_text(src)
                cache.write_text(json.dumps({"license": lic, "mode": mode, "sections": sections}))
                time.sleep(0.5)
            else:
                c = json.loads(cache.read_text()); lic, mode, sections = c["license"], c["mode"], c["sections"]
        except Exception as e:  # keep going; record failure in provenance
            sections, status = [], f"fetch_failed: {type(e).__name__}: {str(e)[:120]}"
        chs = chunk(sections)
        if mode == "excerpt":
            chs = excerpts(chs)
        full_text = "\n\n".join(t for _, t in chs)
        sha = hashlib.sha256(full_text.encode()).hexdigest()[:16] if full_text else None
        if mode == "full" and full_text:
            out = DOCS_DIR / src["category"] / f"{doc_id}.txt"
            out.write_text(f"SOURCE: {src['url']}\nTITLE: {src['title']}\nLICENSE: {lic}\n\n{full_text}")
        con.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (doc_id, src["title"], src["url"], lic, src["category"], mode,
                     str(src.get("publication_date") or ""), now_iso(), sha, len(chs)))
        for i, (loc, t) in enumerate(chs):
            cid = f"{doc_id}#c{i:03d}"
            con.execute("INSERT INTO chunks VALUES (?,?,?,?,?)", (cid, doc_id, loc, t, i))
            con.execute("INSERT INTO chunks_fts(chunk_id, text) VALUES (?,?)", (cid, t))
        prov.append({"doc_id": doc_id, "title": src["title"], "url": src["url"], "license": lic,
                     "stored_mode": mode, "category": src["category"],
                     "publication_date": src.get("publication_date"), "n_chunks": len(chs),
                     "retrieved_at": now_iso(), "sha256_16": sha, "status": status})
        print(f"{doc_id:32s} {mode:8s} {len(chs):4d} chunks  {status}", flush=True)
    con.commit()
    embed_all(con)
    with open(ROOT / "docs" / "provenance.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(prov[0].keys()))
        w.writeheader(); w.writerows(prov)
    return prov


def embed_all(con) -> None:
    from app.memory.retrieval import embedder
    rows = con.execute("SELECT chunk_id, text FROM chunks").fetchall()
    if not rows:
        return
    vecs = embedder().encode([r["text"] for r in rows], normalize_embeddings=True, batch_size=32,
                             show_progress_bar=False).astype(np.float32)
    con.executemany("INSERT INTO chunk_vectors VALUES (?,?,?)",
                    [(r["chunk_id"], vecs.shape[1], v.tobytes()) for r, v in zip(rows, vecs)])
    con.commit()
    print(f"embedded {len(rows)} chunks", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true")
    ingest(fetch=not ap.parse_args().no_fetch)
