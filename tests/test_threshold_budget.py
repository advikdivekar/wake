import numpy as np
import pytest

from training.tabpfn.threshold import best_f1_threshold, tradeoff


def test_best_f1_threshold_separable():
    y = np.array([0, 0, 0, 1, 1]); p = np.array([0.1, 0.2, 0.3, 0.8, 0.9])
    t = best_f1_threshold(y, p)
    assert 0.3 < t <= 0.8


def test_tradeoff_counts():
    y = np.array([0, 1, 1, 0]); p = np.array([0.9, 0.8, 0.1, 0.2])
    row = tradeoff(y, p, [0.5]).iloc[0]
    assert row.missed_anomalies == 1 and row.false_alerts == 1 and row.flagged == 2


def test_decision_bands(monkeypatch):
    from app.prediction import service
    monkeypatch.setattr(service, "thresholds", lambda: {"high": 0.8, "low": 0.05})
    assert service.decide(0.9) == "prioritise" and service.decide(0.5) == "queue" and service.decide(0.01) == "archive"


def test_budget_guard_refuses(monkeypatch, tmp_path):
    from training.tinker import budget
    monkeypatch.setattr(budget, "LEDGER", tmp_path / "ledger.json")
    monkeypatch.setenv("TINKER_BUDGET_USD", "0.01")
    assert budget.authorize("tiny", {"train": 1000}) < 0.01
    with pytest.raises(SystemExit):
        budget.authorize("big", {"train": 10_000_000})
