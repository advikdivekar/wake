import pytest
from fastapi.testclient import TestClient

from app.common.paths import DB_PATH

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="build the database first (make data features db)")


@pytest.fixture(scope="module")
def client():
    from app.api.main import app
    return TestClient(app)


def test_health_and_segments_hide_labels(client):
    assert client.get("/health").status_code == 200
    rows = client.get("/segments?split=test&limit=5").json()
    assert rows and all(r["label"] is None for r in rows)
    seg = client.get(f"/segments/{rows[0]['segment_id']}").json()
    assert seg["segment"]["label"] is None


def test_retrieval_returns_citations():
    from app.memory.retrieval import search
    hits = search("atmospheric reentry 22 May 2024", k=3)
    assert hits and all(h["doc_id"] and h["excerpt"] and h["license"] for h in hits)


def test_card_never_asserts_uncited_cause(client):
    rows = client.get("/segments?split=test&limit=1").json()
    card = client.post("/investigations", json={"segment_id": rows[0]["segment_id"], "use_lm": False}).json()
    assert any("Root cause" in u for u in card["unknown"])
    assert card["ground_truth"] is None
    assert all(s["note"].startswith("Resemblance") for s in card["historical_context"])
    fb = client.post(f"/investigations/{card['card_id']}/feedback", json={"action": "investigate"}).json()
    assert fb["review_status"] == "investigating"


def test_evaluations_missing_file_is_404(client):
    assert client.get("/evaluations/does_not_exist.json").status_code == 404


def test_test_run_guard_refuses_repeat(tmp_path, monkeypatch):
    import training.tabpfn.evaluate as ev
    from app.memory import db
    monkeypatch.setattr(ev, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(ev, "init_db", lambda: db.init_db(tmp_path / "t.db"))
    ev.guard("unit", {"x": 1}, force=False)
    with pytest.raises(SystemExit):
        ev.guard("unit", {"x": 1}, force=False)
