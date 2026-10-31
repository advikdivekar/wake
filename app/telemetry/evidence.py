"""Measured signal evidence for investigation cards (no model involved)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.telemetry.features import gaps, number_of_peaks_finding, zero_runs


def signal_evidence(timestamps, values, sampling: int) -> dict:
    ts = pd.to_datetime(pd.Series(timestamps)).reset_index(drop=True)
    v = np.asarray(values, dtype=float)
    zr = zero_runs(v, min_len=2)
    gp = gaps(ts, sampling)
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
