# Ours vs published (official OPSSAT-AD test split, 529 segments)

Published numbers: Ruszczak et al., Sci Data 2025, Table 3 (see published_benchmark.md).
Our numbers: produced by `python -m training.tabpfn.evaluate` (one guarded test run per config); thresholds chosen on training out-of-fold predictions.

| Model | AUCPR | AUCROC | F1 | Precision | Recall | MCC |
|---|---|---|---|---|---|---|
| **tabpfn-v2:n8:base18+zeros_gaps+autocorr+robust** (ours) | 0.996 [0.989-1.000] | 0.999 | 0.982 [0.963-0.996] | 0.991 | 0.973 | 0.977 |
| **iforest:base18+zeros_gaps+autocorr+robust** (ours) | 0.401 [0.322-0.486] | 0.731 | 0.499 [0.438-0.557] | 0.343 | 0.912 | 0.362 |
| **lightgbm:base18+zeros_gaps+autocorr+robust** (ours) | 0.990 [0.976-0.999] | 0.995 | 0.969 [0.943-0.991] | 0.982 | 0.956 | 0.960 |
| **lr:base18+zeros_gaps+autocorr+robust** (ours) | 0.987 [0.973-0.997] | 0.996 | 0.956 [0.929-0.981] | 0.948 | 0.965 | 0.944 |
| **rf:base18+zeros_gaps+autocorr+robust** (ours) | 0.994 [0.986-0.999] | 0.998 | 0.973 [0.949-0.992] | 1.000 | 0.947 | 0.966 |
| **rule:zero_fraction** (ours) | 0.293 [0.244-0.354] | 0.699 | 0.527 [0.467-0.582] | 0.364 | 0.956 | 0.414 |
| **xgboost:base18+zeros_gaps+autocorr+robust** (ours) | 0.993 [0.983-0.999] | 0.997 | 0.968 [0.943-0.987] | 0.991 | 0.947 | 0.960 |
| FCNN (published best supervised) | 0.979 | 0.989 | 0.946 | 0.963 | 0.929 | 0.932 |
| XGBOD (published) | 0.975 | 0.992 | 0.918 | 0.944 | 0.894 | 0.897 |
| RF+ICCS (published) | 0.963 | 0.985 | 0.883 | 0.978 | 0.805 | 0.862 |
| MO-GAAL (published best unsupervised) | 0.779 | 0.865 | 0.726 | 0.985 | 0.575 | 0.710 |
| IForest (published) | 0.347 | 0.635 | 0.295 | 0.297 | 0.292 | 0.105 |

Brackets: 95% bootstrap CI over test segments. Published results have no CIs; differences within our CI should be read as ties.
