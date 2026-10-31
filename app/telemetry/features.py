"""Feature extraction for OPSSAT-AD segments.

`published_features` is a faithful port of `dataset_generator.ipynb` from
https://github.com/kplabs-pl/OPS-SAT-AD (MIT), including its quirks (pandas
`.seconds`, which wraps at 24 h). `extra_features` adds reproducible signal
descriptors; each is only kept for modelling if training-fold CV justifies it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.signal as sig
from scipy.stats import kurtosis, skew

PUBLISHED_18 = [
    "mean", "var", "std", "len", "duration", "len_weighted", "gaps_squared", "n_peaks",
    "smooth10_n_peaks", "smooth20_n_peaks", "var_div_duration", "var_div_len",
    "diff_peaks", "diff2_peaks", "diff_var", "diff2_var", "kurtosis", "skew",
]


# ---- verbatim port of the published helpers --------------------------------
def number_of_peaks_finding(array: np.ndarray) -> int:
    prominence = 0.1 * (np.max(array) - np.min(array))
    peaks = sig.find_peaks(array, prominence=prominence)[0]
    return len(peaks)


def _duration(ts: pd.Series) -> int:
    t1 = pd.Timestamp(ts.iloc[0])
    t2 = pd.Timestamp(ts.iloc[-1])
    return (t2 - t1).seconds


def _smooth_n_peaks(array: np.ndarray, k: int) -> int:
    kernel = np.ones(k) / k
    return number_of_peaks_finding(np.convolve(array, kernel, mode="same"))


def _gaps_squared(ts: pd.Series) -> float:
    delta = ts.diff().iloc[1:].dt.seconds
    return float((delta ** 2).sum())


def published_features(ts: pd.Series, values: np.ndarray, sampling: int) -> dict:
    ts = pd.to_datetime(ts).reset_index(drop=True)
    v = np.asarray(values, dtype=float)
    f = {
        "duration": _duration(ts),
        "len": len(v),
        "mean": np.mean(v),
        "var": np.var(v),
        "std": np.std(v),
        "kurtosis": kurtosis(v),
        "skew": skew(v),
        "n_peaks": number_of_peaks_finding(v),
        "smooth10_n_peaks": _smooth_n_peaks(v, 10),
        "smooth20_n_peaks": _smooth_n_peaks(v, 20),
        "diff_peaks": number_of_peaks_finding(np.diff(v)),
        "diff2_peaks": number_of_peaks_finding(np.diff(v, n=2)),
        "diff_var": np.var(np.diff(v)),
        "diff2_var": np.var(np.diff(v, n=2)),
        "gaps_squared": _gaps_squared(ts),
    }
    f["len_weighted"] = sampling * f["len"]
    f["var_div_duration"] = f["var"] / f["duration"] if f["duration"] else np.inf
    f["var_div_len"] = f["var"] / f["len"]
    return f


# ---- extra, engineered features ---------------------------------------------
def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return inclusive (start, end) index pairs of True runs."""
    runs, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(mask) - 1))
    return runs


def zero_runs(values: np.ndarray, min_len: int = 2) -> list[tuple[int, int]]:
    v = np.asarray(values, dtype=float)
    return [(s, e) for s, e in _runs(v == 0.0) if e - s + 1 >= min_len]


def gaps(ts: pd.Series, sampling: int, factor: float = 1.5) -> list[tuple[int, float]]:
    """Indices i where the step t[i]-t[i-1] exceeds factor*sampling seconds."""
    ts = pd.to_datetime(ts).reset_index(drop=True)
    d = ts.diff().dt.total_seconds().to_numpy()
    return [(i, float(d[i])) for i in range(1, len(d)) if d[i] > factor * max(sampling, 1)]


def _autocorr(v: np.ndarray, lag: int) -> float:
    if len(v) <= lag + 1 or np.std(v) == 0:
        return 0.0
    return float(np.corrcoef(v[:-lag], v[lag:])[0, 1])


def extra_features(ts: pd.Series, values: np.ndarray, sampling: int, channel: str) -> dict:
    ts = pd.to_datetime(ts).reset_index(drop=True)
    v = np.asarray(values, dtype=float)
    n = len(v)
    zr = zero_runs(v, min_len=1)
    gp = gaps(ts, sampling)
    dt = ts.diff().dt.total_seconds().to_numpy()[1:]
    vc = v - v.mean()
    spec = np.abs(np.fft.rfft(vc)) ** 2 if n > 2 else np.array([0.0])
    spec = spec[1:] if len(spec) > 1 else spec
    psum = spec.sum()
    p = spec / psum if psum > 0 else np.ones_like(spec) / max(len(spec), 1)
    spectral_entropy = float(-(p * np.log(p + 1e-12)).sum() / np.log(max(len(p), 2)))
    q05, q25, q75, q95 = np.percentile(v, [5, 25, 75, 95])
    rng = v.max() - v.min()
    return {
        "duration_total_s": float((ts.iloc[-1] - ts.iloc[0]).total_seconds()),
        "zero_fraction": float(np.mean(v == 0.0)),
        "max_zero_run": int(max((e - s + 1 for s, e in zr), default=0)),
        "n_zero_runs": int(len(zero_runs(v, min_len=2))),
        "gap_count": int(len(gp)),
        "max_gap_s": float(max((g for _, g in gp), default=0.0)),
        "dt_cv": float(np.std(dt) / np.mean(dt)) if len(dt) and np.mean(dt) > 0 else 0.0,
        "spectral_entropy": spectral_entropy,
        "dominant_freq_idx": float(np.argmax(spec) + 1) / max(len(spec), 1),
        "autocorr_lag1": _autocorr(v, 1),
        "autocorr_lag10": _autocorr(v, 10),
        "mad": float(np.median(np.abs(v - np.median(v)))),
        "iqr": float(q75 - q25),
        "q05": float(q05),
        "q95": float(q95),
        "range": float(rng),
        "max_abs_diff_norm": float(np.max(np.abs(np.diff(v))) / rng) if n > 1 and rng > 0 else 0.0,
        "is_magnetometer": int(channel in {"CADC0872", "CADC0873", "CADC0874"}),
    }


def compute_all(segments: pd.DataFrame) -> pd.DataFrame:
    """Compute published + extra features for every segment in segments.csv."""
    rows = []
    for seg_id, g in segments.groupby("segment", sort=True):
        # keep file order: segments are time-monotonic but contain duplicate timestamps,
        # and a non-stable sort would reorder them (changes diff-based features).
        first = g.iloc[0]
        base = {
            "segment": int(seg_id),
            "anomaly": int(first["anomaly"]),
            "train": int(first["train"]),
            "channel": first["channel"],
            "sampling": int(first["sampling"]),
        }
        pub = published_features(g["timestamp"], g["value"].to_numpy(), int(first["sampling"]))
        ext = extra_features(g["timestamp"], g["value"].to_numpy(), int(first["sampling"]), first["channel"])
        rows.append({**base, **pub, **ext})
    return pd.DataFrame(rows)


EXTRA_NAMES = list(
    extra_features(pd.Series(pd.date_range("2020", periods=30, freq="s")), np.arange(30.0), 1, "CADC0872")
)
