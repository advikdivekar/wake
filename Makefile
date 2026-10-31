# The Last Satellite: one command per major step. Run from the repo root.
PY := .venv/bin/python
export PYTHONPATH := $(CURDIR)

.PHONY: setup data features db fixtures api ui ui-fixtures app llm test tabpfn-cv tabpfn-test \
        site site-data docs-ingest tinker-data tinker-base tinker-train tinker-eval adapter offline export post all

setup:            ## create venv + install deps
	uv venv -p 3.11 .venv && uv pip install --python .venv -r requirements.txt
data:             ## download OPSSAT-AD + verify checksums/counts
	$(PY) -m app.ingestion.opssat --download --verify
features:         ## compute features + verify against published dataset.csv
	$(PY) -m app.ingestion.opssat --features
db:               ## build SQLite (telemetry, features)
	$(PY) -m app.memory.db
fixtures:
	$(PY) -m scripts.make_fixtures
tabpfn-cv:        ## CV on the training split only (TabPFN variants + baselines)
	$(PY) -m training.tabpfn.train
tabpfn-test:      ## ONE official test-set run per final config (guarded)
	$(PY) -m training.tabpfn.evaluate
docs-ingest:      ## fetch public documents, chunk, index (FTS5 + vectors)
	$(PY) -m app.ingestion.documents
tinker-data:
	$(PY) -m training.tinker.prepare_sft
tinker-base:
	$(PY) -m training.tinker.evaluate --model base --split val
tinker-train:
	$(PY) -m training.tinker.train
tinker-eval:
	$(PY) -m training.tinker.evaluate --final
adapter:
	$(PY) -m training.tinker.download_adapter
offline:
	HF_HUB_OFFLINE=1 $(PY) -m training.tinker.local_inference --offline
api:
	$(PY) -m uvicorn app.api.main:app --port 8000
ui:
	.venv/bin/streamlit run frontend/Home.py --server.port 8501
ui-fixtures:
	USE_FIXTURES=1 .venv/bin/streamlit run frontend/Home.py --server.port 8501
llm:
	llama-server -m models/Qwen3-8B-Q4_K_M.gguf --lora models/adapter.gguf --port 8081 -c 4096
app:              ## API + UI (+ local LLM if the adapter exists)
	@if [ -f models/adapter.gguf ]; then (llama-server -m models/Qwen3-8B-Q4_K_M.gguf --lora models/adapter.gguf --port 8081 -c 4096 > /tmp/llm.log 2>&1 &); fi
	$(PY) -m uvicorn app.api.main:app --port 8000 & .venv/bin/streamlit run frontend/Home.py --server.port 8501
export:
	$(PY) -m app.investigation.export
post:
	$(PY) -m scripts.fill_post
test:
	$(PY) -m pytest -q tests
all: data features db docs-ingest tabpfn-cv
site-data:        ## export real numbers for the landing site (site/data.js)
	$(PY) -m scripts.build_site_data
site: site-data   ## landing site at http://localhost:8765
	cd site && python3 -m http.server 8765
snapshot:         ## export real API responses for the static web console
	$(PY) -m scripts.export_snapshot
web:              ## cinematic console (dev server; uses the live API on :8000 if running)
	cd web && npm install && npm run dev
web-build:
	cd web && npm ci && npx vite build
