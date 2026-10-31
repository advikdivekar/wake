"""Export a static, labelled snapshot of REAL API responses for the web console (used when no backend is reachable).

Every file is produced by calling the actual FastAPI app (TestClient), so the static site shows genuine outputs:
TabPFN predictions, investigation cards (demo cards written by the local llama.cpp interpreter if it is running),
retrieval answers, timeline, documents and evaluation artefacts.
Usage: python -m scripts.export_snapshot
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app
from app.common.paths import EVAL_DIR, git_sha, now_iso

OUT = Path(__file__).resolve().parents[1] / "web" / "public" / "snapshot"
c = TestClient(app)


def save(name: str, obj) -> None:
    p = OUT / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, separators=(",", ":")))


def get(path):
    r = c.get(path); r.raise_for_status(); return r.json()


def post(path, body):
    r = c.post(path, json=body); r.raise_for_status(); return r.json()


QUESTIONS = [
    "When did OPS-SAT re-enter the atmosphere?",
    "When will OPS-SAT VOLT launch?",
    "What counts as an anomaly in the OPSSAT-AD dataset?",
    "Which channels are photodiodes?",
    "Who annotated the anomalies?",
    "What caused the zero values on the magnetometer channels?",
]
PASSAGES = [
    "On 22 May 2024 the magnetometer I_B_FB_MM_1 reported a run of zero values. The cause may have been a reboot.",
    "Deteriorating components led to undesired reboots and spacecraft recoveries, along with shortening operational windows.",
    "Telemetry from CADC0884 and CADC0886 was sampled every 5 seconds. Some segments contain gaps in the signal.",
]


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for n, p in {"health": "/health", "mission": "/mission", "channels": "/channels", "timeline": "/memory/timeline",
                 "documents": "/documents", "config": "/config"}.items():
        save(n, get(p))
    for ch in [x["channel"] for x in get("/channels")]:
        save(f"telemetry/{ch}", get(f"/channels/{ch}/telemetry?max_points=2500"))
    queue = get("/segments?split=test&sort=probability&limit=600")
    save("segments_test", queue)
    demo = get("/demo")
    save("demo", demo)
    for d in demo:
        sid = d["segment_id"]
        save(f"demo/{sid}_steps", get(f"/demo/{sid}/steps"))
        save(f"demo/{sid}_reveal", get(f"/demo/{sid}/reveal"))
    # queue drawer: top-40 + a band around the threshold, deterministic template cards (labelled)
    ids = [q["segment_id"] for q in queue[:40]] + [q["segment_id"] for q in queue if 0.3 <= (q["probability"] or 0) <= 0.8][:10]
    for sid in dict.fromkeys(ids):
        save(f"segment/{sid}", get(f"/segments/{sid}"))
        save(f"card/{sid}", post("/investigations", {"segment_id": sid, "use_lm": False}))
    save("ask", [post("/memory/ask", {"question": q, "k": 6}) for q in QUESTIONS])
    save("extract", [{"text": t, "record": post("/memory/extract", {"text": t})} for t in PASSAGES])
    evals = {}
    for p in sorted(EVAL_DIR.iterdir()):
        if p.suffix in (".json", ".csv", ".md") and not p.name.startswith("."):
            evals[p.name] = get(f"/evaluations/{p.name}")
    save("evaluations", evals)
    save("manifest", {"kind": "archived snapshot of real API responses", "created_at": now_iso(), "git_sha": git_sha(),
                      "note": "Static fallback for the web console. Queue cards use the deterministic template; demo cards "
                              "use the local interpreter if it was running at export time."})
    print("snapshot files:", sum(1 for _ in OUT.rglob("*.json")))


if __name__ == "__main__":
    main()
