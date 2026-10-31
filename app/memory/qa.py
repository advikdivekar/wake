"""Mission Memory question answering over the archive, always with citations and an explicit 'missing' list.

With an LM backend the interpreter answers in task-C format from the retrieved sources; the answer is accepted
only if every cited source index exists and the quoted definition is verbatim. Otherwise (or with no LM) a
deterministic extractive answer is produced from the best-matching retrieved sentences.
"""
from __future__ import annotations

import re

from app.memory.retrieval import search
from training.tinker import spec
from training.tinker.prepare_sft import SYS_C

STOP = set("the a an of to in on for and or is was were what when how why which who did does do are be by with from "
           "that this it its as at about any there their".split())


SYN = {"reenter": "reentr", "reentry": "reentr", "deorbit": "reentr", "launch": "launch"}


def _norm(t: str) -> str:
    t = t.lower().replace("re-ent", "reent").replace("re-enter", "reenter")
    return re.sub(r"[^a-z0-9_ ]", " ", t)


def _stem(t: str) -> str:
    t = SYN.get(t, t)
    return t if "_" in t or len(t) <= 5 else t[:6]


def _terms(q: str) -> list[str]:
    return list(dict.fromkeys(_stem(t) for t in _words(q)))


def _words(q: str) -> list[str]:
    return [t for t in _norm(q).split() if t not in STOP and len(t) > 2 and t not in ("ops", "sat", "opssat")]


def _candidates(text: str) -> list[str]:
    cands = spec.sentences(text) + [l.strip() for l in text.splitlines() if 20 <= len(l.strip()) <= 300]
    return [c for c in dict.fromkeys(cands) if not re.match(r"^(\d+\.|↑|\^|\[\d)", c)]


def answer(question: str, k: int = 6) -> dict:
    expanded = question
    if re.search(r"re-?ent|deorbit", question, re.I):
        expanded += " reentry re-entry atmospheric deorbited"
    if re.search(r"\b(why|cause|caused|reason|early|earlier)\b", question, re.I):
        expanded += " caused by due to impacted by"
    if re.search(r"experiment", question, re.I):
        expanded += " experiments teams countries"
    hits = search(expanded, k=k)
    terms = _terms(question)
    why = bool(re.search(r"\b(why|cause|caused|reason)\b", question, re.I))
    CAUSAL = re.compile(r"\b(caused by|due to|because|resulted in|impacted by|led to|as a result of)\b", re.I)
    scored = []
    for h in hits:
        for s in _candidates(h["excerpt"]):
            ns = _norm(s)
            overlap = sum(1 for t in terms if t in ns) / max(len(terms), 1)
            if overlap and 30 <= len(s) <= 400:
                scored.append((overlap, s, h))
    scored.sort(key=lambda x: -x[0])
    citations, picked = [], []
    for score, s, h in scored:
        if score < 0.34 or len(picked) == 3:
            break
        if s not in picked:
            picked.append(s)
            citations.append({**{k_: h[k_] for k_ in ("doc_id", "chunk_id", "title", "url", "location", "license")},
                              "excerpt": s, "score": round(score, 3)})
    missing = []
    covered = {t for t in terms if any(t in _norm(c["excerpt"]) for c in citations)}
    gaps = [w for w in dict.fromkeys(_words(question)) if _stem(w) not in covered]
    if not citations:
        missing.append("The archive contains no passage that addresses this question.")
    elif gaps:
        missing.append(f"No archived passage mentions: {', '.join(gaps)}.")
    if re.search(r"\b(why|cause|caused|reason)\b", question, re.I) and not any(
            re.search(r"\b(caused by|due to|because|resulted|impacted by|led to|as a result of)\b", c["excerpt"], re.I) for c in citations):
        missing.append("No archived source states a cause; the cause remains unknown.")
    text = " ".join(f"{c['excerpt']} [{i}]" for i, c in enumerate(citations, 1)) or "Not found in the archive."
    model = "extractive (deterministic)"
    try:
        from app.investigation.lm import get_lm
        lm = get_lm()
        if not lm.name.startswith("template") and hits:
            srcs = "\n\n".join(f"[{i}] ({h['chunk_id']}) {h['excerpt'][:700]}" for i, h in enumerate(hits[:3], 1))
            out = lm.chat([{"role": "system", "content": SYS_C},
                           {"role": "user", "content": f"TERM: {question}\n\nSOURCES:\n{srcs}"}], max_tokens=200)
            m = re.search(r"DEFINITION:\s*(.+)", out); src = re.search(r"SOURCE:\s*\[?(\d+)", out)
            if m and src and m.group(1).strip() != "?" and 1 <= int(src.group(1)) <= 3:
                h = hits[int(src.group(1)) - 1]
                lm_overlap = sum(1 for t in terms if t in _norm(m.group(1))) / max(len(terms), 1)
                best = scored[0][0] if scored else 0
                if spec.norm_ws(m.group(1)) in spec.norm_ws(h["excerpt"]) and lm_overlap >= best:
                    text = f"{m.group(1).strip()} [1]"
                    citations = [{**{k_: h[k_] for k_ in ("doc_id", "chunk_id", "title", "url", "location", "license")},
                                  "excerpt": m.group(1).strip(), "score": h["score"]}]
                    model = lm.name
    except Exception:
        pass
    return {"question": question, "answer": text, "citations": citations, "missing": missing, "model": model}
