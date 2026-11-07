"""Compatibility import path. Prefer `bjj_pipeline.organizer`."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_NEW = "bjj_pipeline.organizer"
_pkg = importlib.import_module(_NEW)
sys.modules[__name__] = _pkg
for _name in (
    "artwork",
    "chapters",
    "concat",
    "errors",
    "fanatics_search",
    "httputil",
    "layout",
    "match",
    "models",
    "naming",
    "nfo",
    "pipeline",
    "repair",
    "split",
    "scrape",
    "scrape.base",
    "scrape.bjj_fanatics",
):
    sys.modules[f"{__name__}.{_name}"] = importlib.import_module(f"{_NEW}.{_name}")
