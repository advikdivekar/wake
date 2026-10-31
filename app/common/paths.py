"""Central paths and small helpers shared across the project."""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw" / "opssat"
DATA_PROCESSED = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "data" / "documents"
EVAL_DIR = ROOT / "evaluations"
MODELS_DIR = ROOT / "models"
DB_PATH = DATA_PROCESSED / "mission.db"

for _p in (DATA_RAW, DATA_PROCESSED, EVAL_DIR, MODELS_DIR):
    _p.mkdir(parents=True, exist_ok=True)


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "uncommitted"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def write_eval_json(name: str, payload: dict, produced_by: str) -> Path:
    """Write an evaluation artefact with provenance metadata."""
    out = {"produced_by": produced_by, "git_sha": git_sha(), "created_at": now_iso(), **payload}
    path = EVAL_DIR / name
    path.write_text(json.dumps(out, indent=2, default=_json_default))
    return path


def _json_default(o):
    import numpy as np

    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)
