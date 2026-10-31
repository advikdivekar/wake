# Licensing notes

| Component | Licence | What it means here |
|---|---|---|
| **OPSSAT-AD dataset** (Zenodo 10.5281/zenodo.12588359) | **CC-BY-4.0** (per the Zenodo record) | Downloaded at build time and not redistributed in this repo. Attribution: Ruszczak, Kotowski, Evans, Nalepa. *The master prompt assumed MIT; the Zenodo record says CC-BY-4.0, and that is what we cite.* |
| **OPS-SAT-AD code** (kplabs-pl/OPS-SAT-AD) | **MIT** | Our feature extractor is a port of `dataset_generator.ipynb`. The notebook is ingested as a document (MIT, with attribution). |
| **OPSSAT-AD paper** (Sci Data 2025) and its arXiv preprint | **CC-BY-4.0** | Full text stored and chunked with attribution. |
| **TabPFN v2 weights** (used for all reported results) | **Prior Labs License** (Apache-2.0 + attribution requirement) | Downloaded by the `tabpfn` package without a Hugging Face login. "Built with TabPFN" attribution is in the README and the app footer. |
| TabPFN-2.5 / 2.6 / 3 weights | Non-commercial licences (gated on Hugging Face) | **Not used** in the reported results (no HF token was available). Code supports them via `HF_TOKEN` + `TABPFN_EXTRA_VERSIONS`; if used, the product becomes non-commercial. |
| **Qwen3-8B** base model | Apache-2.0 | Public GGUF (`Qwen/Qwen3-8B-GGUF`, Q4_K_M) used for local inference. |
| **LoRA adapter** | Derived from Qwen3-8B (Apache-2.0); trained on the public documents below | Trained on Tinker's hosted service, then downloaded. Inference is local. |
| Wikipedia "OPS-SAT" | CC-BY-SA-4.0 | Full text stored with attribution. Derived records inherit share-alike. |
| ESA web pages, ESA indico PDFs, news reprints, TU Graz, SmallSat/USU | Website terms / all rights reserved | **Excerpts only** (≤300 characters × ≤10 per source) plus a link. Never stored in full. |
| SatNOGS DB, ICCS 2023 (Springer) | CC-BY-SA / paywalled | **Metadata only**. |
| llama.cpp converter (`third_party/`, git-ignored) | MIT | Used to convert the PEFT adapter to GGUF. |

The provenance of every stored document (URL, licence, stored mode, retrieval time, hash) is in `docs/provenance.csv`.
