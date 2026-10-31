from __future__ import annotations

import os
from functools import lru_cache

import yaml
from dotenv import load_dotenv

from app.common.paths import ROOT

load_dotenv(ROOT / ".env")


@lru_cache
def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default
