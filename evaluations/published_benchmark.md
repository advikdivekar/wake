# Published OPSSAT-AD benchmark (the bar)

**Source:** B. Ruszczak, K. Kotowski, D. Evans, J. Nalepa, *"The OPS-SAT benchmark for detecting anomalies in satellite telemetry"*, **Scientific Data** 12 (2025), DOI [10.1038/s41597-025-05035-3](https://doi.org/10.1038/s41597-025-05035-3), CC-BY-4.0. PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC12041257/. Preprint: arXiv [2407.04730](https://arxiv.org/abs/2407.04730).

The correction notice (Sci Data 2025;12:1445, https://pmc.ncbi.nlm.nih.gov/articles/PMC12361492/) only re-ordered Figures 3–10. **It changed no tables.**

**Setting:** Table 3, "universal detector" (one model across all channels), 18 hand-crafted features, official test split Ψ = 529 segments. The numbers below were transcribed from the PMC HTML on 2026-10-31. On the same day they were **re-verified programmatically** against the Europe PMC JATS full text (`https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12041257/fullTextXML`).

## Supervised: top rows of Table 3

| Model | AUCPR | AUCROC | Accuracy | F1 | Precision | Recall | MCC |
|---|---|---|---|---|---|---|---|
| **FCNN** | **0.979** | 0.989 | **0.977** | **0.946** | 0.963 | **0.929** | **0.932** |
| XGBOD | 0.975 | **0.992** | 0.966 | 0.918 | 0.944 | 0.894 | 0.897 |
| RF+ICCS | 0.963 | 0.985 | 0.955 | 0.883 | 0.978 | 0.805 | 0.862 |
| LSVC | 0.934 | 0.968 | 0.926 | 0.808 | 0.911 | 0.726 | 0.771 |
| LR | 0.931 | 0.969 | 0.924 | 0.800 | 0.920 | 0.708 | 0.764 |
| AdaBoost | 0.923 | 0.962 | 0.934 | 0.836 | 0.890 | 0.788 | 0.797 |
| Linear+L2 | 0.901 | 0.958 | 0.905 | 0.722 | 0.970 | 0.575 | 0.703 |

Paper text: FCNN had "four false positives and eight false negatives of all Ψ samples".

## Unsupervised: selected rows of Table 3

| Model | AUCPR | AUCROC | Accuracy | F1 | Precision | Recall | MCC |
|---|---|---|---|---|---|---|---|
| **MO-GAAL** (best unsupervised by AUCPR, F1, MCC) | 0.779 | 0.865 | 0.907 | 0.726 | 0.985 | 0.575 | 0.710 |
| KNN | 0.658 | 0.852 | 0.824 | 0.575 | 0.594 | 0.558 | 0.465 |
| OCSVM | 0.659 | 0.787 | 0.845 | 0.647 | 0.630 | 0.664 | 0.548 |
| IForest | 0.347 | 0.635 | 0.701 | 0.295 | 0.297 | 0.292 | 0.105 |

The paper benchmarks 30 methods in total. The underlining that marks "best unsupervised" in the paper did not survive HTML extraction, so the best-unsupervised call above is our reading of the numbers.

## The bar we chase
- **Best published supervised:** FCNN, with AUCPR 0.979, F1 0.946, MCC 0.932, recall 0.929.
- **Best published AUROC:** XGBOD, 0.992.
- **Best published unsupervised:** MO-GAAL, with AUCPR 0.779 and F1 0.726.

## Caveats when comparing
- **The paper's split counts disagree.** Its text says 1,494 training segments, but its own class counts (1,273 + 321) and the released data both give **1,594**. See `dataset_verification.json`.
- **Thresholds may differ.** The paper's F1/precision/recall/MCC use each method's own decision rule. Ours uses a threshold chosen on training-set out-of-fold predictions (`threshold_tradeoff.csv`).
- **Table 4 (specialised per-channel models) is a different setting.** It covers 6 channels with the `len` and `duration` features dropped, so it is not the bar for a universal detector. Its best rows, verified against the JATS XML:

| Model (Table 4) | AUCPR | AUCROC | Accuracy | F1 | Precision | Recall | MCC |
|---|---|---|---|---|---|---|---|
| LR | 0.946 | 0.974 | 0.944 | 0.873 | 0.924 | 0.832 | 0.840 |
| LinearSVC | 0.939 | 0.966 | 0.957 | 0.898 | 0.956 | 0.849 | 0.873 |
| FCNN | 0.924 | 0.953 | 0.970 | 0.929 | 0.979 | 0.886 | 0.912 |
- **We did not re-run the published models.** The numbers above are quoted from the paper.
