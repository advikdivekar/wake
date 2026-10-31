# COST_LOG (Tinker)

Prices are per 1M tokens, from https://thinkingmachines.ai/tinker/pricing/ (dated 2026-10-19).
Qwen3-8B: prefill $0.195, sample $0.60, train $0.44.

Estimates are made locally before each job by `training/tinker/budget.py`. Actual spend comes from `tinker billing usage`.

| time | job | tokens | est. USD | cumulative |
|---|---|---|---|---|
| 2026-10-31T16:08:36+00:00 | train:lc-n50 | {'train': 56691} | 0.0249 | 0.0249 |
| 2026-10-31T16:10:39+00:00 | eval:tuned-lc-n50:val | {'prefill': 32392, 'sample': 24200} | 0.0208 | 0.0457 |
| 2026-10-31T16:11:18+00:00 | train:lc-n100 | {'train': 110691} | 0.0487 | 0.0944 |
| 2026-10-31T16:12:22+00:00 | eval:tuned-lc-n100:val | {'prefill': 32392, 'sample': 24200} | 0.0208 | 0.1152 |
| 2026-10-31T16:12:30+00:00 | train:lc-n200 | {'train': 219954} | 0.0968 | 0.2120 |
| 2026-10-31T16:13:35+00:00 | eval:tuned-lc-n200:val | {'prefill': 32392, 'sample': 24200} | 0.0208 | 0.2328 |
| 2026-10-31T16:14:10+00:00 | train:lc-nall (spec v1, STOPPED at step 65/84) | {'train': 392004} | 0.1725 | 0.4053 |
| 2026-10-31T16:20:09+00:00 | train:final-v2 | {'train': 508785} | 0.2239 | 0.6292 |
| 2026-10-31T16:21:38+00:00 | eval:tuned-final-v2:val | {'prefill': 33292, 'sample': 24200} | 0.0210 | 0.6502 |
| 2026-10-31T16:22:54+00:00 | eval:base:test | {'prefill': 65294, 'sample': 29400} | 0.0304 | 0.6806 |
| 2026-10-31T16:23:50+00:00 | eval:tuned-final-v2:test | {'prefill': 65294, 'sample': 29400} | 0.0304 | 0.7110 |
| 2026-10-31T16:35:09+00:00 | train:offline-n200-v2 | {'train': 224640} | 0.0988 | 0.8098 |
| 2026-10-31T16:47:30+00:00 | eval:tuned-offline-n200-v2:val | {'prefill': 33292, 'sample': 24200} | 0.0210 | 0.8308 |
