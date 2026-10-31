"""Shared data, feature sets, CV splitter, metrics and model factories for the TabPFN phase.

The official OPSSAT-AD test split (train==0) is NEVER touched here except by evaluate.py.
"""
from __future__ import annotations

import os

# NOTE: xgboost/lightgbm and torch (tabpfn) ship different OpenMP runtimes. Loading both in one
# process segfaults on macOS (exit 139 / "OMP: Error #179"). TabPFN and tree baselines therefore
# always run in SEPARATE processes (see train.py / evaluate.py --stage).
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, f1_score, matthews_corrcoef, precision_score,
                             recall_score, roc_auc_score, confusion_matrix, brier_score_loss)
from sklearn.model_selection import StratifiedGroupKFold

from app.common.paths import DATA_PROCESSED
from app.telemetry.features import EXTRA_NAMES, PUBLISHED_18

warnings.filterwarnings("ignore")
SEED = 2137  # same seed as the OPSSAT-AD modelling notebook

CHANNEL_ONEHOT = [f"ch_{c}" for c in ["CADC0872", "CADC0873", "CADC0874", "CADC0884", "CADC0886",
                                     "CADC0888", "CADC0890", "CADC0892", "CADC0894"]]
EXTRA_GROUPS = {
    "zeros_gaps": ["zero_fraction", "max_zero_run", "n_zero_runs", "gap_count", "max_gap_s", "dt_cv",
                   "duration_total_s"],
    "spectral": ["spectral_entropy", "dominant_freq_idx"],
    "autocorr": ["autocorr_lag1", "autocorr_lag10"],
    "robust": ["mad", "iqr", "q05", "q95", "range", "max_abs_diff_norm"],
    "channel": ["is_magnetometer", "sampling"] + CHANNEL_ONEHOT,
}
assert set(sum((v for k, v in EXTRA_GROUPS.items() if k != "channel"), [])) | {"is_magnetometer"} == set(EXTRA_NAMES)


def load_frame() -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED / "features.csv")
    for c in CHANNEL_ONEHOT:
        df[c] = (df["channel"] == c[3:]).astype(int)
    num = df.select_dtypes("number").columns
    df[num] = df[num].replace([np.inf, -np.inf], np.nan)
    return df


def feature_list(groups: list[str]) -> list[str]:
    cols = list(PUBLISHED_18)
    for g in groups:
        cols += [c for c in EXTRA_GROUPS[g] if c not in cols]
    return cols


def cv_groups(df: pd.DataFrame, block: int = 10) -> np.ndarray:
    """Group contiguous segments of the same channel so neighbours never straddle folds."""
    order = df.groupby("channel")["segment"].rank(method="first").astype(int) - 1
    return (df["channel"] + "_" + (order // block).astype(str)).to_numpy()


def splitter(n_splits=5):
    return StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)


def metrics(y, p, thr=0.5) -> dict:
    yhat = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    return {
        "auprc": average_precision_score(y, p), "auroc": roc_auc_score(y, p),
        "f1": f1_score(y, yhat, zero_division=0), "precision": precision_score(y, yhat, zero_division=0),
        "recall": recall_score(y, yhat, zero_division=0), "mcc": matthews_corrcoef(y, yhat),
        "accuracy": float((yhat == y).mean()), "brier": brier_score_loss(y, p),
        "confusion": [[int(tn), int(fp)], [int(fn), int(tp)]], "threshold": thr,
    }


def tabpfn_versions() -> list[str]:
    """V2 always (no token needed). Gated versions only if HF_TOKEN is configured."""
    vs = ["v2"]
    if os.environ.get("HF_TOKEN"):
        vs += [v.strip() for v in os.environ.get("TABPFN_EXTRA_VERSIONS", "v2.5").split(",") if v.strip()]
    return vs


def device() -> str:
    os.environ.setdefault("TABPFN_ALLOW_CPU_LARGE_DATASET", "1")
    return os.environ.get("TABPFN_DEVICE", "mps")


def make_tabpfn(version="v2", n_estimators=8):
    from tabpfn import TabPFNClassifier
    from tabpfn.constants import ModelVersion
    mv = {m.value: m for m in ModelVersion}[version]
    return TabPFNClassifier.create_default_for_version(mv, n_estimators=n_estimators, device=device(),
                                                       random_state=SEED)


def signed_log(X):
    return np.sign(X) * np.log1p(np.abs(X))


def make_baseline(name: str):
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import FunctionTransformer, StandardScaler
    imp = SimpleImputer(strategy="median")
    if name == "lr":
        return make_pipeline(imp, FunctionTransformer(signed_log), StandardScaler(),
                             LogisticRegression(C=1.0, max_iter=5000, class_weight="balanced"))
    if name == "rf":
        return make_pipeline(imp, RandomForestClassifier(n_estimators=500, min_samples_leaf=1,
                                                         class_weight="balanced_subsample",
                                                         n_jobs=-1, random_state=SEED))
    if name == "xgboost":
        from xgboost import XGBClassifier
        return make_pipeline(imp, XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05,
                                                subsample=0.9, colsample_bytree=0.8, eval_metric="logloss",
                                                random_state=SEED, n_jobs=-1))
    if name == "lightgbm":
        from lightgbm import LGBMClassifier
        return make_pipeline(imp, LGBMClassifier(n_estimators=400, num_leaves=15, learning_rate=0.05,
                                                 subsample=0.9, colsample_bytree=0.8, random_state=SEED,
                                                 verbose=-1))
    if name == "iforest":
        return make_pipeline(imp, FunctionTransformer(signed_log), StandardScaler(),
                             _IForestProba(contamination=0.2))
    raise ValueError(name)


from sklearn.base import BaseEstimator, ClassifierMixin  # noqa: E402


class _IForestProba(ClassifierMixin, BaseEstimator):
    """Unsupervised Isolation Forest exposing a [0,1] anomaly score as predict_proba (fit ignores y)."""

    def __init__(self, contamination=0.2):
        self.contamination = contamination

    def fit(self, X, y=None):
        from sklearn.ensemble import IsolationForest
        self.m_ = IsolationForest(n_estimators=500, contamination=self.contamination, random_state=SEED).fit(X)
        s = -self.m_.score_samples(X)
        self.lo_, self.hi_ = s.min(), s.max()
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        s = np.clip((-self.m_.score_samples(X) - self.lo_) / (self.hi_ - self.lo_ + 1e-12), 0, 1)
        return np.c_[1 - s, s]


class ZeroFractionRule:
    """Heuristic: score = fraction of exact-zero samples + normalised gap count (no learning)."""

    def fit(self, X, y=None):
        return self

    def predict_proba(self, Xdf):
        s = np.clip(Xdf["zero_fraction"].fillna(0).to_numpy() * 5 + (Xdf["gap_count"].fillna(0).to_numpy() > 0) * 0.5, 0, 1)
        return np.c_[1 - s, s]
