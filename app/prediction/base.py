"""Swappable tabular-classifier interface."""
from __future__ import annotations

import abc

import numpy as np


class TabularClassifier(abc.ABC):
    name: str
    features: list[str]

    @abc.abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(anomalous) for each row."""


class PickledClassifier(TabularClassifier):
    """Loads a {model, features, name} pickle produced by training/tabpfn/evaluate.py (TabPFN or any sklearn model)."""

    def __init__(self, path):
        import pickle
        with open(path, "rb") as f:
            d = pickle.load(f)
        self.model, self.features, self.name = d["model"], d["features"], d["name"]

    def predict_proba(self, X):
        return self.model.predict_proba(X)[:, 1]
