"""Measured signal evidence for investigation cards (no model involved)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.telemetry.features import gaps, number_of_peaks_finding, zero_runs


def significant_gaps(ts: pd.Series, sampling: int) -> list[tuple[int, float]]:
    """Display-level gaps: a step longer than max(3 x median step, 3 x sampling period).
    (The model feature `gap_count` keeps its own, trained definition in app/telemetry/features.py.)"""
    ts = pd.to_datetime(pd.Series(ts)).reset_index(drop=True)
    d = ts.diff().dt.total_seconds().to_numpy()
    if len(d) < 3:
        return []
    thr = max(3 * float(np.nanmedian(d[1:])), 3 * max(sampling, 1))
    return [(i, float(d[i])) for i in range(1, len(d)) if d[i] > thr]


def signal_evidence(timestamps, values, sampling: int) -> dict:
    ts = pd.to_datetime(pd.Series(timestamps)).reset_index(drop=True)
    v = np.asarray(values, dtype=float)
    zr = zero_runs(v, min_len=2)
    gp = significant_gaps(ts, sampling)
    dt = ts.diff().dt.total_seconds().to_numpy()[1:]
    irregular = bool(len(dt) and (np.std(dt) / max(np.mean(dt), 1e-9)) > 0.5)
    noise = float(np.std(np.diff(v))) if len(v) > 1 else 0.0
    return {
        "zero_runs": len(zr),
        "max_zero_run": int(max((e - s + 1 for s, e in zr), default=0)),
        "gap_count": len(gp),
        "max_gap_s": float(max((g for _, g in gp), default=0.0)),
        "n_peaks": int(number_of_peaks_finding(v)) if len(v) > 2 and v.max() > v.min() else 0,
        "irregular_sampling": irregular,
        "noise_std": noise,
    }
