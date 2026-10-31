import json

import numpy as np
import pandas as pd
import pytest

from app.common.paths import DATA_RAW, EVAL_DIR
from app.telemetry.features import PUBLISHED_18, extra_features, number_of_peaks_finding, published_features, zero_runs


def _seg(values, step=1):
    ts = pd.Series(pd.date_range("2022-01-01", periods=len(values), freq=f"{step}s"))
    return ts, np.asarray(values, dtype=float)


def test_peak_count_uses_10pct_prominence():
    v = np.zeros(100); v[20] = 1.0; v[60] = 1.0; v[80] = 0.05   # third bump is below 10% prominence
    assert number_of_peaks_finding(v) == 2


def test_published_feature_names_and_derived_relations():
    ts, v = _seg(np.sin(np.linspace(0, 6, 120)))
    f = published_features(ts, v, sampling=5)
    assert set(PUBLISHED_18) <= set(f)
    assert f["len"] == 120 and f["len_weighted"] == 600
    assert f["var_div_len"] == pytest.approx(f["var"] / 120)
    assert f["duration"] == 119 and f["gaps_squared"] == 119


def test_zero_runs_and_extras():
    v = [1, 0, 0, 0, 2, 0, 3, 0, 0]
    assert zero_runs(np.array(v, float)) == [(1, 3), (7, 8)]
    ts, arr = _seg(v)
    e = extra_features(ts, arr, 1, "CADC0872")
    assert e["max_zero_run"] == 3 and e["is_magnetometer"] == 1
    assert e["zero_fraction"] == pytest.approx(6 / 9)


def test_gaps_detected():
    ts = pd.Series(pd.to_datetime(["2022-01-01 00:00:00", "2022-01-01 00:00:01", "2022-01-01 00:00:30",
                                   "2022-01-01 00:00:31"]))
    e = extra_features(ts, np.array([1.0, 2, 3, 4]), 1, "CADC0884")
    assert e["gap_count"] == 1 and e["max_gap_s"] == 29


@pytest.mark.skipif(not (EVAL_DIR / "feature_reproduction.json").exists(), reason="run make features first")
def test_reproduction_report_meets_bar():
    r = json.loads((EVAL_DIR / "feature_reproduction.json").read_text())
    assert r["overall_pct_within_tol"] > 0.999
    assert all(v["pct_within_tol"] == 1.0 for k, v in r["features"].items() if "smooth" not in k)


@pytest.mark.skipif(not (DATA_RAW / "dataset.csv").exists(), reason="data not downloaded")
def test_reproduces_first_published_rows():
    seg = pd.read_csv(DATA_RAW / "segments.csv", nrows=5000, parse_dates=["timestamp"])
    ref = pd.read_csv(DATA_RAW / "dataset.csv").set_index("segment")
    for sid, g in list(seg.groupby("segment"))[:3]:
        if len(g) != ref.loc[sid, "len"]:
            continue   # segment truncated by nrows
        f = published_features(g["timestamp"], g["value"].to_numpy(), int(g["sampling"].iloc[0]))
        for k in ("mean", "var", "kurtosis", "n_peaks", "diff_var", "gaps_squared"):
            assert f[k] == pytest.approx(ref.loc[sid, k], rel=1e-6, abs=1e-12)
