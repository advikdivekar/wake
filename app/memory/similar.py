"""Similar historical segments: k-NN in standardised feature space over the TRAINING split, with labels.
Framed strictly as resemblance in measured characteristics, not as evidence of a shared fault."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from app.common.paths import DATA_PROCESSED, EVAL_DIR

NOTE = "Resemblance in measured characteristics, not evidence of a shared fault."


@lru_cache
def _index():
    df = pd.read_csv(DATA_PROCESSED / "features.csv").replace([np.inf, -np.inf], np.nan)
    feats = json.loads((EVAL_DIR / "tabpfn_selection.json").read_text())["features"]
    X = df[feats].astype(float)
    X = np.sign(X) * np.log1p(np.abs(X))
    med, iqr = X[df.train == 1].median(), (X[df.train == 1].quantile(0.75) - X[df.train == 1].quantile(0.25)).replace(0, 1)
    Z = ((X - med) / iqr).fillna(0).clip(-10, 10).to_numpy()
    return df, Z


def similar(segment_id: int, k: int = 5) -> list[dict]:
    df, Z = _index()
    idx = df.index[df.segment == segment_id]
    if not len(idx):
        return []
    q = Z[idx[0]]
    train = np.where((df.train == 1).to_numpy() & (df.segment != segment_id).to_numpy())[0]
    d = np.linalg.norm(Z[train] - q, axis=1)
    order = train[np.argsort(d)[:k]]
    return [{"segment_id": int(df.segment[i]), "distance": round(float(np.linalg.norm(Z[i] - q)), 3),
             "label": int(df.anomaly[i]), "channel": df.channel[i], "note": NOTE} for i in order]
