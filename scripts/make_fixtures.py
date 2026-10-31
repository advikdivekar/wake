"""Write frontend/fixtures/*.json so the UI can be built before the backend is complete.

Endpoints that already work are captured from the real API (real data). Shapes for not-yet-built
endpoints are hand-written EXAMPLES with placeholder values. Every fixture is marked
illustrative=true; list payloads are wrapped as {"illustrative": true, "data": [...]}.
"""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app

OUT = Path(__file__).resolve().parents[1] / "frontend" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)
c = TestClient(app)


def save(name, payload):
    if isinstance(payload, list):
        payload = {"illustrative": True, "data": payload}
    else:
        payload = {"illustrative": True, **payload}
    (OUT / f"{name}.json").write_text(json.dumps(payload, indent=1))


for name, path in {
    "health": "/health", "mission": "/mission", "channels": "/channels", "config": "/config",
    "segments": "/segments?split=test&limit=50", "segment_1": "/segments/1",
    "features_1": "/segments/1/features", "telemetry_CADC0872": "/channels/CADC0872/telemetry?max_points=3000",
    "evaluations": "/evaluations",
}.items():
    save(name, c.get(path).json())

cite = {"doc_id": "opssat-ad-paper", "chunk_id": "opssat-ad-paper#c000", "title": "EXAMPLE citation title",
        "url": "https://doi.org/10.1038/s41597-025-05035-3", "location": "EXAMPLE", "excerpt": "EXAMPLE excerpt text",
        "score": 0.5, "license": "CC-BY-4.0"}
pred = {"segment_id": 1, "probability": 0.5, "decision": "queue", "thresholds": {"high": 0.6, "low": 0.3},
        "model": "EXAMPLE", "contributors": [{"feature": "gaps_squared", "value": 309.0, "z": 1.0,
                                              "importance": 0.05, "plain": "EXAMPLE explanation"}]}
sim = [{"segment_id": 2, "distance": 0.4, "label": 1, "channel": "CADC0872",
        "note": "Resemblance in measured characteristics, not evidence of a shared fault."}]
card = {"card_id": "inv-1-1", "segment_id": 1, "created_at": "2026-10-31T00:00:00Z", "prediction": pred,
        "signal_evidence": {"zero_runs": 0, "max_zero_run": 0, "gap_count": 1, "max_gap_s": 31.0, "n_peaks": 4,
                            "irregular_sampling": False, "noise_std": 1e-6},
        "historical_context": sim, "documents": [cite],
        "known": [{"statement": "EXAMPLE measured statement", "basis": "measured", "citations": []},
                  {"statement": "EXAMPLE cited statement", "basis": "cited", "citations": [cite]}],
        "unknown": ["Root cause of this signal behaviour is not documented in the archive"],
        "suggested_action": "EXAMPLE action", "summary": "EXAMPLE summary", "summary_model": "EXAMPLE",
        "review_status": "unreviewed", "ground_truth": None}
save("prediction_1", pred)
save("similar_1", sim)
save("card_1", card)
save("card_1_revealed", {**card, "ground_truth": 1})
save("cards", [card])
save("ask", {"question": "EXAMPLE question", "answer": "EXAMPLE answer", "citations": [cite],
             "missing": ["EXAMPLE: the archive contains no incident report for this"], "model": "EXAMPLE"})
save("extract", {"record_id": "rec-0001", "channel_id": None, "sensor_type": "magnetometer", "units": None,
                 "event_date": None, "publication_date": "2025-04-29", "observation": "EXAMPLE",
                 "operational_response": None, "root_cause": None, "evidence_excerpt": "EXAMPLE",
                 "unknown_fields": ["root_cause", "units"], "source": cite})
save("timeline", [{"event_date": "2024-05-22", "publication_date": None, "event": "EXAMPLE event", "citation": cite}])
save("documents", [{"doc_id": "opssat-ad-paper", "title": "EXAMPLE", "url": cite["url"], "license": "CC-BY-4.0",
                    "stored_mode": "full", "n_chunks": 10, "retrieved_at": "2026-10-31", "category": "research"}])
save("document_opssat-ad-paper", {"document": {"doc_id": "opssat-ad-paper", "title": "EXAMPLE"},
                                  "chunks": [{"chunk_id": "opssat-ad-paper#c000", "location": "EXAMPLE", "text": "EXAMPLE"}]})
save("demo", [{"segment_id": 1, "blurb": "EXAMPLE blurb"}])
seg1 = c.get("/segments/1").json()
save("demo_steps_1", {**seg1, "features": c.get("/segments/1/features").json(), "prediction": pred,
                      "citations": [cite], "similar": sim, "card": card})
save("demo_reveal_1", {"segment_id": 1, "label": 1, "case": "TP", "predicted": 1, "probability": 0.5})
print("fixtures:", len(list(OUT.glob("*.json"))))
